import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as scheduler from 'aws-cdk-lib/aws-scheduler';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
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
    const surveyRes = customerRes.addResource('survey');
    surveyRes.addMethod('POST', customerOpsInt, customerOpts);
    surveyRes.addResource('results').addMethod('GET', customerOpsInt, customerOpts);
    customerRes.addResource('reminder').addMethod('POST', customerOpsInt, customerOpts);

    // ── n8n EC2 t3.micro (Free Tier) ─────────────────────────────────────────
    const vpc = ec2.Vpc.fromLookup(this, 'DefaultVpc', { isDefault: true });

    const n8nSg = new ec2.SecurityGroup(this, 'N8nSG', {
      vpc,
      description: 'n8n security group',
      allowAllOutbound: true,
    });
    n8nSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(80),   'HTTP');
    n8nSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(443),  'HTTPS');
    n8nSg.addIngressRule(ec2.Peer.anyIpv4(), ec2.Port.tcp(5678), 'n8n direct');

    const n8nUserData = ec2.UserData.forLinux();
    n8nUserData.addCommands(
      // Amazon Linux 2023 — dnf, Node.js 20 natively available
      'dnf update -y',
      'dnf install -y nodejs nginx',
      'node --version && npm --version',
      'npm install -g n8n',
      // n8n systemd service
      'mkdir -p /opt/n8n',
      `cat > /etc/systemd/system/n8n.service << 'SVCEOF'
[Unit]
Description=n8n workflow automation
After=network.target

[Service]
Type=simple
User=root
Environment=N8N_BASIC_AUTH_ACTIVE=true
Environment=N8N_BASIC_AUTH_USER=admin
Environment=N8N_BASIC_AUTH_PASSWORD=pientuottajat2025
Environment=N8N_HOST=0.0.0.0
Environment=N8N_PORT=5678
Environment=N8N_PROTOCOL=http
Environment=WEBHOOK_URL=http://localhost:5678
Environment=N8N_USER_FOLDER=/opt/n8n
ExecStart=/usr/local/bin/n8n start
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
SVCEOF`,
      'systemctl daemon-reload',
      'systemctl enable n8n',
      'systemctl start n8n',
      // Nginx reverse proxy port 80 -> n8n 5678
      `cat > /etc/nginx/conf.d/n8n.conf << 'NGXEOF'
server {
    listen 80;
    server_name _;
    location / {
        proxy_pass http://localhost:5678;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
NGXEOF`,
      'rm -f /etc/nginx/conf.d/default.conf',
      'systemctl enable nginx',
      'systemctl start nginx',
    );

    const n8nInstance = new ec2.Instance(this, 'N8nInstance', {
      vpc,
      instanceType: ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
      machineImage: ec2.MachineImage.latestAmazonLinux2023(),
      securityGroup: n8nSg,
      userData: n8nUserData,
      vpcSubnets: { subnetType: ec2.SubnetType.PUBLIC },
      // SSM access for debugging
      role: new iam.Role(this, 'N8nInstanceRole', {
        assumedBy: new iam.ServicePrincipal('ec2.amazonaws.com'),
        managedPolicies: [
          iam.ManagedPolicy.fromAwsManagedPolicyName('AmazonSSMManagedInstanceCore'),
        ],
      }),
    });

    const n8nEip = new ec2.CfnEIP(this, 'N8nEIP');
    new ec2.CfnEIPAssociation(this, 'N8nEIPAssoc', {
      instanceId: n8nInstance.instanceId,
      eip: n8nEip.ref,
    });

    // ── Outputs ──────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'N8nUrl', {
      value: `http://${n8nEip.ref}`,
      description: 'n8n ops-työkalu kaupan henkilöstölle — admin/pientuottajat2025',
    });
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
