from aws_cdk import (
    core as cdk,
    aws_lambda as lambda_,
    aws_dynamodb as dynamodb,
    aws_events,
    aws_events_targets,
    aws_apigateway as apigw
)


class WebShellMgStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # create dynamodb table
        web_shell_table = dynamodb.Table(
            self, "web_shell_table",
            partition_key=dynamodb.Attribute(
                name="id",
                type=dynamodb.AttributeType.STRING
            )
        )

        # create producer lambda function
        producer_lambda = lambda_.Function(self, "producer_lambda_function",
                                              runtime=lambda_.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              code=lambda_.Code.asset("./web_shell_mg/lambda/producer"))

        producer_lambda.add_environment("TABLE_NAME", web_shell_table.table_name)

        # grant permission to lambda to write to webshell table
        web_shell_table.grant_write_data(producer_lambda)

        # create consumer lambda function
        consumer_lambda = lambda_.Function(self, "consumer_lambda_function",
                                              runtime=lambda_.Runtime.PYTHON_3_7,
                                              handler="lambda_function.lambda_handler",
                                              code=lambda_.Code.asset("./web_shell_mg/lambda/consumer"))

        consumer_lambda.add_environment("TABLE_NAME", web_shell_table.table_name)

        # grant permission to lambda to read from webshell table
        web_shell_table.grant_read_data(consumer_lambda)

        # create a Cloudwatch Event rule
        one_minute_rule = aws_events.Rule(
            self, "one_minute_rule",
            schedule=aws_events.Schedule.rate(cdk.Duration.minutes(1)),
        )

        # Add target to Cloudwatch Event
        one_minute_rule.add_target(aws_events_targets.LambdaFunction(producer_lambda))
        one_minute_rule.add_target(aws_events_targets.LambdaFunction(consumer_lambda))

        # create api gateway
        base_api = apigw.RestApi(self, 'WebShellApiGateway',
                                  rest_api_name='WebShellApiGateway')

        #create stats api endpoint
        web_shell_stats = base_api.root.add_resource('stats')
        web_shell_stats_lambda_integration = apigw.LambdaIntegration(consumer_lambda, proxy=False, integration_responses=[
            {
                'statusCode': '200',
                'responseParameters': {
                    'method.response.header.Access-Control-Allow-Origin': "'*'",
                }
            }
        ]
        )

        web_shell_stats.add_method('GET', web_shell_stats_lambda_integration,
                                  method_responses=[{
                                      'statusCode': '200',
                                      'responseParameters': {
                                          'method.response.header.Access-Control-Allow-Origin': True,
                                      }
                                  }
                                  ]
                                  )
