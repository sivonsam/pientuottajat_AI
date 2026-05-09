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

    // ── SQS ──────────────────────────────────────────────────────────────────
    const notificationQueue = new sqs.Queue(this, 'NotificationQueue', {
      queueName: 'pientuottajat-notifications',
      visibilityTimeout: cdk.Duration.seconds(60),
    });

    // ── Lambda Layer (Python deps) ────────────────────────────────────────────
    const pythonLayer = new lambda.LayerVersion(this, 'PythonDepsLayer', {
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../backend/layers/python')),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
      description: 'python-telegram-bot + boto3',
    });

    // ── Bedrock permissions (suora InvokeModel, halvempi kuin Agents demossa) ──
    const bedrockPolicy = new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: ['arn:aws:bedrock:*::foundation-model/anthropic.claude-3-haiku-20240307-v1:0'],
    });

    // ── Webhook Lambda (Telegram → Bedrock Agent) ─────────────────────────────
    const webhookLambda = new lambda.Function(this, 'WebhookHandler', {
      functionName: 'pientuottajat-webhook',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../backend/lambdas/webhook')),
      layers: [pythonLayer],
      timeout: cdk.Duration.seconds(30),
      environment: {
        DYNAMODB_TABLE_SUPPLIERS: suppliersTable.tableName,
        DYNAMODB_TABLE_CONVERSATIONS: conversationsTable.tableName,
        WHATSAPP_PHONE_NUMBER_ID: process.env.WHATSAPP_PHONE_NUMBER_ID ?? '',
        WHATSAPP_VERIFY_TOKEN: process.env.WHATSAPP_VERIFY_TOKEN ?? '',
        BEDROCK_MODEL_ID: 'anthropic.claude-3-haiku-20240307-v1:0',
        USE_MOCK_DATA: 'True',
      },
    });

    webhookLambda.addToRolePolicy(bedrockPolicy);
    suppliersTable.grantReadWriteData(webhookLambda);
    conversationsTable.grantReadWriteData(webhookLambda);
    waSecret.grantRead(webhookLambda);

    // ── Action Groups Lambda (Bedrock → data) ─────────────────────────────────
    const actionGroupsLambda = new lambda.Function(this, 'ActionGroupsHandler', {
      functionName: 'pientuottajat-action-groups',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'action_groups.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../backend/agents')),
      timeout: cdk.Duration.seconds(30),
      environment: {
        DYNAMODB_TABLE_SUPPLIERS: suppliersTable.tableName,
        USE_MOCK_DATA: 'True',
      },
    });

    suppliersTable.grantReadWriteData(actionGroupsLambda);

    // Salli Bedrock kutsua action groups -lambdaa
    actionGroupsLambda.addPermission('BedrockInvoke', {
      principal: new iam.ServicePrincipal('bedrock.amazonaws.com'),
      action: 'lambda:InvokeFunction',
    });

    // ── Notifier Lambda (SQS → WhatsApp/Telegram) ────────────────────────────
    const notifierLambda = new lambda.Function(this, 'NotifierHandler', {
      functionName: 'pientuottajat-notifier',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'handler.lambda_handler',
      code: lambda.Code.fromAsset(path.join(__dirname, '../../../backend/lambdas/notifier')),
      timeout: cdk.Duration.seconds(30),
      environment: {
        DYNAMODB_TABLE_SUPPLIERS: suppliersTable.tableName,
      },
    });

    suppliersTable.grantReadData(notifierLambda);
    notifierLambda.addEventSource(new SqsEventSource(notificationQueue, { batchSize: 10 }));
    waSecret.grantRead(notifierLambda);

    // ── EventBridge Scheduler — Kuukausiraportti (ilmainen taso, korvaa Step Functions demossa) ──
    const schedulerRole = new iam.Role(this, 'SchedulerRole', {
      assumedBy: new iam.ServicePrincipal('scheduler.amazonaws.com'),
    });
    notifierLambda.grantInvoke(schedulerRole);

    new scheduler.CfnSchedule(this, 'MonthlyReportSchedule', {
      name: 'pientuottajat-monthly-report',
      scheduleExpression: 'cron(0 8 1 * ? *)', // 1. päivä klo 8:00
      flexibleTimeWindow: { mode: 'OFF' },
      target: {
        arn: notifierLambda.functionArn,
        roleArn: schedulerRole.roleArn,
        input: JSON.stringify({ Records: [{ body: JSON.stringify({ event_type: 'monthly_report', broadcast: true }) }] }),
      },
    });

    // ── API Gateway ──────────────────────────────────────────────────────────
    const api = new apigateway.RestApi(this, 'PientuottajatApi', {
      restApiName: 'pientuottajat-api',
      description: 'Pientuottajat AI webhook endpoint',
    });

    const webhook = api.root.addResource('webhook');
    const telegramWebhook = webhook.addResource('whatsapp');
    telegramWebhook.addMethod('GET', new apigateway.LambdaIntegration(webhookLambda));  // Meta verify
    telegramWebhook.addMethod('POST', new apigateway.LambdaIntegration(webhookLambda)); // Saapuvat viestit

    // ── Outputs ──────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
      description: 'API Gateway URL — aseta tämä Telegram webhook-osoitteeksi',
    });

    new cdk.CfnOutput(this, 'WhatsAppWebhookUrl', {
      value: `${api.url}webhook/whatsapp`,
      description: 'Aseta tama Meta Business -konsoliin: WhatsApp -> Configuration -> Webhook Callback URL',
    });

    new cdk.CfnOutput(this, 'NotificationQueueUrl', {
      value: notificationQueue.queueUrl,
      description: 'SQS notification queue URL',
    });

    new cdk.CfnOutput(this, 'ActionGroupsLambdaArn', {
      value: actionGroupsLambda.functionArn,
      description: 'Käytä tätä ARNia Bedrock Agent Action Group -konfiguraatiossa',
    });
  }
}
