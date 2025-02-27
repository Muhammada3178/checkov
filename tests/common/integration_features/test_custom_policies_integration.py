import json
import os
import types
import unittest

from checkov.common.bridgecrew.integration_features.features.custom_policies_integration import \
    CustomPoliciesIntegration
from checkov.common.bridgecrew.platform_integration import BcPlatformIntegration
from checkov.common.checks_infra.checks_parser import NXGraphCheckParser
from checkov.common.checks_infra.registry import Registry, get_graph_checks_registry
from checkov.common.models.enums import CheckResult
from checkov.common.output.record import Record
from checkov.common.output.report import Report
from checkov.terraform.runner import Runner as TerraformRunner
from checkov.cloudformation.runner import Runner as CFNRunner
from checkov.runner_filter import RunnerFilter
from pathlib import Path


class TestCustomPoliciesIntegration(unittest.TestCase):
    def tearDown(self) -> None:
        get_graph_checks_registry("cloudformation").checks = []
        get_graph_checks_registry("terraform").checks = []

    def test_integration_valid(self):
        instance = BcPlatformIntegration()
        instance.skip_download = False
        instance.platform_integration_configured = True

        custom_policies_integration = CustomPoliciesIntegration(instance)

        self.assertTrue(custom_policies_integration.is_valid())

        instance.skip_download = True
        self.assertFalse(custom_policies_integration.is_valid())

        instance.platform_integration_configured = False
        self.assertFalse(custom_policies_integration.is_valid())

        instance.skip_download = False
        self.assertFalse(custom_policies_integration.is_valid())

        custom_policies_integration.integration_feature_failures = True
        self.assertFalse(custom_policies_integration.is_valid())

    def test_policy_load(self):
        # response from API
        policies = [
            {
                "id": "mikepolicies_AWS_1625063607541",
                "title": "yaml1",
                "severity": "MEDIUM",
                "category": "General",
                "guideline": "yaml1",
                "code": json.dumps({
                    "or": [
                        {
                            "value": "xyz",
                            "operator": "equals",
                            "attribute": "xyz",
                            "cond_type": "attribute",
                            "resource_types": [
                                "aws_s3_bucket"
                            ]
                        }
                    ]
                }),
                "benchmarks": {},
            },
            {
                "id": "mikepolicies_aws_1625063842021",
                "title": "ui1",
                "severity": "HIGH",
                "category": "General",
                "guideline": "ui1",
                "code": json.dumps({
                    "value": "abc",
                    "operator": "equals",
                    "attribute": "region",
                    "cond_type": "attribute",
                    "resource_types": [
                        "aws_s3_bucket"
                    ]
                }),
                "benchmarks": {},
            },
            {
                "id": "kpande_AWS_1635180094606",
                "title": "Check that all EC2 instances are tagged with yor_trace",
                "descriptiveTitle": "null",
                "constructiveTitle": "null",
                "severity": "LOW",
                "pcSeverity": "null",
                "category": "General",
                "guideline": "Check for YOR tagging",
                "code": json.dumps({
                    "operator": "exists",
                    "attribute": "Tags.yor_trace",
                    "cond_type": "attribute",
                    "resource_types": [
                        "AWS::EC2::Instance"
                    ]
                }),
                "benchmarks": {},
                "frameworks": [
                    "Terraform",
                    "CloudFormation"
                ],
            },
            {
                "id": "kpande_AWS_1635187541652",
                "title": "Custom - ensure MSK Cluster logging is enabled",
                "descriptiveTitle": "null",
                "constructiveTitle": "null",
                "severity": "MEDIUM",
                "pcSeverity": "null",
                "category": "Logging",
                "resourceTypes": [
                    "AWS::MSK::Cluster"
                ],
                "accountsData": {},
                "guideline": "Some sample guidelines",
                "isCustom": True,
                "code": json.dumps({
                    "or": [
                        {
                            "value": "true",
                            "operator": "equals",
                            "attribute": "LoggingInfo.BrokerLogs.S3.Enabled",
                            "cond_type": "attribute",
                            "resource_types": [
                                "AWS::MSK::Cluster"
                            ]
                        },
                        {
                            "value": "true",
                            "operator": "equals",
                            "attribute": "LoggingInfo.BrokerLogs.Firehose.Enabled",
                            "cond_type": "attribute",
                            "resource_types": [
                                "AWS::MSK::Cluster"
                            ]
                        },
                        {
                            "value": "true",
                            "operator": "equals",
                            "attribute": "LoggingInfo.BrokerLogs.CloudWatchLogs.Enabled",
                            "cond_type": "attribute",
                            "resource_types": [
                                "AWS::MSK::Cluster"
                            ]
                        }
                    ]
                }),
                "benchmarks": {},
                "frameworks": [
                    "Terraform",
                    "CloudFormation"
                ],
            }
        ]

        # for this test, we simulate some of the check registry manipulation; otherwise the singleton
        # instance will be modified and break other tests.

        parser = NXGraphCheckParser()

        registry = Registry(parser=NXGraphCheckParser(), checks_dir=str(
            Path(__file__).parent.parent.parent.parent / "checkov" / "terraform" / "checks" / "graph_checks"))
        checks = [parser.parse_raw_check(CustomPoliciesIntegration._convert_raw_check(p)) for p in policies]
        registry.checks = checks  # simulate that the policy downloader will do

        tf_runner = TerraformRunner(external_registries=[registry])
        cfn_runner = CFNRunner(external_registries=[registry])
        current_dir = os.path.dirname(os.path.realpath(__file__))

        test_files_dir = current_dir + "/example_custom_policy_dir"

        report = tf_runner.run(root_folder=test_files_dir, runner_filter=RunnerFilter())
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'mikepolicies_aws_1625063842021']), 1)
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'mikepolicies_AWS_1625063607541']), 1)

        report = tf_runner.run(root_folder=test_files_dir,
                               runner_filter=RunnerFilter(checks=['mikepolicies_aws_1625063842021']))
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'mikepolicies_aws_1625063842021']), 1)
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'mikepolicies_AWS_1625063607541']), 0)

        report = tf_runner.run(root_folder=test_files_dir,
                               runner_filter=RunnerFilter(skip_checks=['mikepolicies_aws_1625063842021']))
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'mikepolicies_aws_1625063842021']), 0)
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'mikepolicies_AWS_1625063607541']), 1)

        report = cfn_runner.run(root_folder=test_files_dir,
                                runner_filter=RunnerFilter(checks=['kpande_AWS_1635187541652']))
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'kpande_AWS_1635187541652']), 6)
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'kpande_AWS_1635180094606']), 0)

        report = cfn_runner.run(root_folder=test_files_dir,
                                runner_filter=RunnerFilter(checks=['kpande_AWS_1635180094606']))
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'kpande_AWS_1635180094606']), 1)
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'kpande_AWS_1635187541652']), 0)

        report = cfn_runner.run(root_folder=test_files_dir,
                                runner_filter=RunnerFilter(skip_checks=['kpande_AWS_1635180094606']))
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'kpande_AWS_1635180094606']), 0)
        self.assertEqual(len([r for r in report.failed_checks if r.check_id == 'kpande_AWS_1635187541652']), 6)

    def test_pre_scan_with_cloned_checks(self):
        instance = BcPlatformIntegration()
        instance.skip_download = False
        instance.platform_integration_configured = True
        custom_policies_integration = CustomPoliciesIntegration(instance)

        instance.customer_run_config_response = mock_custom_policies_response()

        custom_policies_integration.pre_scan()
        self.assertEqual(1, len(custom_policies_integration.bc_cloned_checks))

    def test_post_runner_with_cloned_checks(self):
        instance = BcPlatformIntegration()
        instance.skip_download = False
        instance.platform_integration_configured = True
        custom_policies_integration = CustomPoliciesIntegration(instance)

        # mock _get_policies_from_platform method
        instance.customer_run_config_response = mock_custom_policies_response()
        custom_policies_integration.pre_scan()

        scan_reports = Report("terraform")
        record = Record(
            check_id="CKV_AWS_5",
            check_name="Ensure all data stored in the Elasticsearch is securely encrypted at rest",
            check_result={"result": CheckResult.FAILED},
            code_block=[],
            file_path="./main.tf",
            file_line_range=[7, 10],
            resource="aws_elasticsearch_domain.enabled",
            evaluations=None,
            check_class='',
            file_abs_path=",.",
            entity_tags={"tag1": "value1"},
            bc_check_id="BC_AWS_ELASTICSEARCH_3"
        )
        scan_reports.failed_checks.append(record)

        custom_policies_integration.post_runner(scan_reports)
        self.assertEqual(2, len(scan_reports.failed_checks))
        self.assertEqual('mikepolicies_cloned_AWS_1625063607541', scan_reports.failed_checks[1].check_id)


def mock_custom_policies_response():
    return {
        "customPolicies": [
            {
                "id": "mikepolicies_cloned_AWS_1625063607541",
                "title": "Cloned policy",
                "severity": "CRITICAL",
                "category": "General",
                "resourceTypes": [
                    "aws_s3_bucket"
                ],
                "guideline": "mikepolicies_cloned_AWS_1625063607541",
                "benchmarks": {},
                "createdBy": "mike+policies@bridgecrew.io",
                "code": "null",
                "sourceIncidentId": "BC_AWS_ELASTICSEARCH_3"
            }
        ]
    }

if __name__ == '__main__':
    unittest.main()
