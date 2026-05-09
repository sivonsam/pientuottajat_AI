import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { Construct } from 'constructs';
import * as path from 'path';

export class PientuottajatStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const WA_TOKEN      = process.env.WHATSAPP_TOKEN           ?? '';
    const WA_PHONE_ID   = process.env.WHATSAPP_PHONE_NUMBER_ID ?? '';
    const WA_VERIFY     = process.env.WHATSAPP_VERIFY_TOKEN    ?? '';
    const AGENT_ID      = process.env.BEDROCK_AGENT_ID         ?? '';
    const AGENT_ALIAS   = process.env.BEDROCK_AGENT_ALIAS_ID   ?? 'TSTALIASID';

    // ── Secrets ──────────────────────────────────────────────────────────────
    const waSecret = new secretsmanager.Secret(this, 'WaSecret', {
      secretName: 'pientuottajat/whatsapp-token',
      description: 'WhatsApp Business API token',
    });

    // ── DynamoDB ──────────────────────────────────────────────────────────────
    const suppliersTable = new dynamodb.Table(this, 'SuppliersTable', {
      tableName: 'pientuottajat-suppliers',
      partitionKey: { name: 'supplier_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const conversationsTable = new dynamodb.Table(this, 'ConversationsTable', {
      tableName: 'pientuottajat-conversations',
      partitionKey: { name: 'session_id', type: dynamodb.AttributeType.STRING },
      timeToLiveAttribute: 'ttl',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // Kyselyt: kaupan puolelta toimittajille lahetettavat surveyt
    const surveysTable = new dynamodb.Table(this, 'SurveysTable', {
      tableName: 'pientuottajat-surveys',
      partitionKey: { name: 'id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });

    // ── SQS — event fan-out ──────────────────────────────────────────────────
    const eventQueue = new sqs.Queue(this, 'EventQueue', {
      queueName: 'pientuottajat-events',
      visibilityTimeout: cdk.Duration.seconds(60),
    });

    // ── Yhteiset ympäristömuuttujat ──────────────────────────────────────────
    const commonEnv = {
      WHATSAPP_TOKEN:           WA_TOKEN,
      WHATSAPP_PHONE_NUMBER_ID: WA_PHONE_ID,
      DYNAMODB_TABLE_SUPPLIERS: suppliersTable.tableName,
      AWS_ACCOUNT:              this.account,
    };

    // ── Bedrock permissions ──────────────────────────────────────────────────
    const bedrockPolicy = new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel', 'bedrock:InvokeAgent'],
      resources: ['*'],
    });

    // ── Lambda: Webhook (toimittaja → WhatsApp → Bedrock Agent) ─────────────
    const webhookLambda = new lambda.Function(this, 'WebhookHandler', {
      functionName: 'pientuottajat-webhook',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../backend/lambdas/webhook')),
      timeout: cdk.Duration.seconds(29),  // API GW max 29s
      environment: {
        ...commonEnv,
        WHATSAPP_VERIFY_TOKEN:      WA_VERIFY,
        DYNAMODB_TABLE_CONVERSATIONS: conversationsTable.tableName,
        BEDROCK_AGENT_ID:           AGENT_ID,
        BEDROCK_AGENT_ALIAS_ID:     AGENT_ALIAS,
        BEDROCK_MODEL_ID:           'anthropic.claude-3-haiku-20240307-v1:0',
        USE_MOCK_DATA:              'True',
      },
    });
    webhookLambda.addToRolePolicy(bedrockPolicy);
    suppliersTable.grantReadWriteData(webhookLambda);
    conversationsTable.grantReadWriteData(webhookLambda);
    waSecret.grantRead(webhookLambda);

    // ── Lambda: Action Groups (Bedrock Agent → data) ─────────────────────────
    const actionGroupsLambda = new lambda.Function(this, 'ActionGroupsHandler', {
      functionName: 'pientuottajat-action-groups',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'action_groups.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../backend/agents')),
      timeout: cdk.Duration.seconds(30),
      environment: {
        DYNAMODB_TABLE_SUPPLIERS: suppliersTable.tableName,
        DYNAMODB_TABLE_SURVEYS:   surveysTable.tableName,
        USE_MOCK_DATA:            'True',
      },
    });
    suppliersTable.grantReadWriteData(actionGroupsLambda);
    surveysTable.grantReadWriteData(actionGroupsLambda);
    actionGroupsLambda.addPermission('BedrockInvoke', {
      principal: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      action: 'lambda:InvokeFunction',
    });

    // ── Lambda: Customer Ops (kaupan puoli) ──────────────────────────────────
    const customerOpsLambda = new lambda.Function(this, 'CustomerOpsHandler', {
      functionName: 'pientuottajat-customer-ops',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../backend/lambdas/customer_ops')),
      timeout: cdk.Duration.seconds(30),
      environment: {
        ...commonEnv,
        DYNAMODB_TABLE_SURVEYS:  surveysTable.tableName,
        SQS_NOTIFICATION_QUEUE_URL: eventQueue.queueUrl,
      },
    });
    suppliersTable.grantReadData(customerOpsLambda);
    surveysTable.grantReadWriteData(customerOpsLambda);
    eventQueue.grantSendMessages(customerOpsLambda);
    waSecret.grantRead(customerOpsLambda);

    // ── Lambda: Event Processor (SQS → proaktiiviset WhatsApp-viestit) ───────
    const eventProcessorLambda = new lambda.Function(this, 'EventProcessorHandler', {
      functionName: 'pientuottajat-event-processor',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../backend/lambdas/event_processor')),
      timeout: cdk.Duration.seconds(60),
      environment: { ...commonEnv },
    });
    suppliersTable.grantReadData(eventProcessorLambda);
    eventProcessorLambda.addEventSource(new SqsEventSource(eventQueue, { batchSize: 10 }));
    waSecret.grantRead(eventProcessorLambda);

    // ── EventBridge Scheduler — kuukausiraportti ─────────────────────────────
    const schedulerRole = new iam.Role(this, 'SchedulerRole', {
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
    });
    eventProcessorLambda.grantInvoke(schedulerRole);
    new scheduler.CfnSchedule(this, 'MonthlyReport', {
      name: 'pientuottajat-monthly-report',
      scheduleExpression: 'cron(0 8 1 * ? *)',
      flexibleTimeWindow: { mode: 'OFF' },
      target: {
        arn: eventProcessorLambda.functionArn,
        roleArn: schedulerRole.roleArn,
        input: JSON.stringify({ Records: [{ body: JSON.stringify({ event_type: 'monthly_report' }) }] }),
      },
    });

    // ── API Gateway ──────────────────────────────────────────────────────────
    const api = new apigateway.RestApi(this, 'PientuottajatApi', {
      restApiName: 'pientuottajat-api',
      description: 'Pientuottajat AI — webhook & customer ops',
    });

    // API Key kaupan puolen endpointille
    const apiKey = new apigateway.ApiKey(this, 'CustomerApiKey', {
      apiKeyName: 'pientuottajat-customer-key',
      description: 'API-avain kaupan henkilöstölle',
    });
    const usagePlan = new apigateway.UsagePlan(this, 'CustomerUsagePlan', {
      name: 'pientuottajat-customer',
      apiStages: [{ api, stage: api.deploymentStage }],
      throttle: { rateLimit: 10, burstLimit: 20 },
    });
    usagePlan.addApiKey(apiKey);

    // /webhook/whatsapp — toimittajat
    const webhook = api.root.addResource('webhook').addResource('whatsapp');
    webhook.addMethod('GET',  new apigateway.LambdaIntegration(webhookLambda));
    webhook.addMethod('POST', new apigateway.LambdaIntegration(webhookLambda));

    // /customer/* — kaupan henkilöstö (API key vaaditaan)
    const customerRes = api.root.addResource('customer');
    const customerOpsInt = new apigateway.LambdaIntegration(customerOpsLambda);
    const customerOpts = { apiKeyRequired: true };

    customerRes.addResource('broadcast').addMethod('POST', customerOpsInt, customerOpts);
    customerRes.addResource('survey').addMethod('POST', customerOpsInt, customerOpts);
    const surveyResults = customerRes.addResource('survey').addResource('results');
    surveyResults.addMethod('GET', customerOpsInt, customerOpts);
    customerRes.addResource('reminder').addMethod('POST', customerOpsInt, customerOpts);

    // ── Outputs ──────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'WhatsAppWebhookUrl', {
      value: `${api.url}webhook/whatsapp`,
      description: 'Meta Business konsoliin: WhatsApp -> Configuration -> Webhook Callback URL',
    });
    new cdk.CfnOutput(this, 'CustomerApiUrl', {
      value: `${api.url}customer/`,
      description: 'Kaupan henkilöstön API-osoite',
    });
    new cdk.CfnOutput(this, 'ActionGroupsLambdaArn', {
      value: actionGroupsLambda.functionArn,
      description: 'Kayta tata ARNia Bedrock Agent Action Group -konfiguraatiossa',
    });
    new cdk.CfnOutput(this, 'EventQueueUrl', {
      value: eventQueue.queueUrl,
      description: 'SQS-jono eventtien syottamiseen (reklamaatiot, hyllypuutteet jne.)',
    });
  }
}
