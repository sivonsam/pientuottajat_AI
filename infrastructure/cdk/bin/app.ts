#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { PientuottajatStack } from '../lib/pientuottajat-stack';

const app = new cdk.App();

new PientuottajatStack(app, 'PientuottajatAI', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? 'eu-west-1',
  },
  description: 'Pientuottajat AI — proaktiivinen agenttinen ratkaisu',
});
