from checkov.common.models.enums import CheckCategories, CheckResult
from checkov.terraform.checks.resource.base_resource_check import BaseResourceCheck


class RDSIsPublic(BaseResourceCheck):
    def __init__(self):
        name = "Ensure database instance is not public"
        id = "CKV_ALI_9"
        supported_resources = ['alicloud_db_instance']
        categories = [CheckCategories.ENCRYPTION]
        super().__init__(name=name, id=id, categories=categories, supported_resources=supported_resources)

    def scan_resource_conf(self, conf):
        if conf.get("security_ips") and isinstance(conf.get("security_ips"), list):
            addresses = conf.get("security_ips")[0]
            if "0.0.0.0" in addresses or "0.0.0.0/0" in addresses:
                return CheckResult.FAILED
        return CheckResult.PASSED


check = RDSIsPublic()
