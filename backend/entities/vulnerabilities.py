# cybersec_project/backend/entities/vulnerabilities.py

from typing import List, Dict, Any, Optional
from enum import Enum

class VulnerabilitySeverity(Enum):
    """Defines standard severity levels for vulnerabilities."""
    INFO = "Info"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class VulnerabilityCategory(Enum):
    """Broad categories for vulnerabilities."""
    CODE_EXECUTION = "Code Execution"
    INFORMATION_DISCLOSURE = "Information Disclosure"
    PRIVILEGE_ESCALATION = "Privilege Escalation"
    DENIAL_OF_SERVICE = "Denial of Service"
    ACCESS_CONTROL_BYPASS = "Access Control Bypass"
    DATA_MANIPULATION = "Data Manipulation"
    OTHER = "Other"

class Vulnerability:
    """
    Represents a specific vulnerability that can exist on a Node.
    """
    def __init__(self,
                 vuln_id: str, # A unique identifier, e.g., "CVE-2023-12345" or "SQLi_WebApp_Login"
                 name: str,
                 description: str,
                 severity: VulnerabilitySeverity,
                 category: VulnerabilityCategory,
                 cvss_score: Optional[float] = None, # Common Vulnerability Scoring System score
                 affected_components: Optional[List[str]] = None, # e.g., ["WebApp Framework v1.2", "OS Kernel v5.x"]
                 mitre_attack_ids: Optional[List[str]] = None, # Relevant MITRE ATT&CK Technique IDs
                 patch_difficulty: int = 5, # Arbitrary scale 1-10 for how hard it is to patch
                 exploit_difficulty: int = 5, # Arbitrary scale 1-10 for how hard it is to exploit
                 metadata: Optional[Dict[str, Any]] = None):
        """
        Initializes a Vulnerability object.

        Args:
            vuln_id (str): Unique identifier for the vulnerability.
            name (str): A human-readable name for the vulnerability.
            description (str): A brief description of the vulnerability.
            severity (VulnerabilitySeverity): The severity level.
            category (VulnerabilityCategory): The category of the vulnerability.
            cvss_score (Optional[float], optional): CVSS score, if available. Defaults to None.
            affected_components (Optional[List[str]], optional): Components/software affected. Defaults to None.
            mitre_attack_ids (Optional[List[str]], optional): Associated MITRE ATT&CK technique IDs. Defaults to None.
            patch_difficulty (int, optional): Difficulty to patch (1-10). Defaults to 5.
            exploit_difficulty (int, optional): Difficulty to exploit (1-10). Defaults to 5.
            metadata (Optional[Dict[str, Any]], optional): Additional custom data. Defaults to None.
        """
        self.vuln_id: str = vuln_id
        self.name: str = name
        self.description: str = description
        self.severity: VulnerabilitySeverity = severity
        self.category: VulnerabilityCategory = category
        self.cvss_score: Optional[float] = cvss_score
        self.affected_components: List[str] = affected_components if affected_components is not None else []
        self.mitre_attack_ids: List[str] = mitre_attack_ids if mitre_attack_ids is not None else []
        self.patch_difficulty: int = patch_difficulty
        self.exploit_difficulty: int = exploit_difficulty
        self.metadata: Dict[str, Any] = metadata if metadata is not None else {}

    def __repr__(self) -> str:
        return f"Vulnerability(id='{self.vuln_id}', name='{self.name}', severity='{self.severity.value}')"

    def to_dict(self) -> Dict[str, Any]:
        """Serializes the Vulnerability object to a dictionary."""
        return {
            "vuln_id": self.vuln_id,
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value, # Store the enum value as string
            "category": self.category.value, # Store the enum value as string
            "cvss_score": self.cvss_score,
            "affected_components": self.affected_components,
            "mitre_attack_ids": self.mitre_attack_ids,
            "patch_difficulty": self.patch_difficulty,
            "exploit_difficulty": self.exploit_difficulty,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Vulnerability':
        """Creates a Vulnerability object from a dictionary."""
        return cls(
            vuln_id=data["vuln_id"],
            name=data["name"],
            description=data["description"],
            severity=VulnerabilitySeverity(data["severity"]), # Rehydrate enum from string value
            category=VulnerabilityCategory(data["category"]), # Rehydrate enum from string value
            cvss_score=data.get("cvss_score"),
            affected_components=data.get("affected_components"),
            mitre_attack_ids=data.get("mitre_attack_ids"),
            patch_difficulty=data.get("patch_difficulty", 5),
            exploit_difficulty=data.get("exploit_difficulty", 5),
            metadata=data.get("metadata")
        )

class VulnerabilityRegistry:
    """
    A central registry to store and manage all known vulnerability definitions.
    This ensures that vulnerability data is defined in one place and can be easily
    referenced by Nodes and Actions using their `vuln_id`.
    """
    def __init__(self):
        self._vulnerabilities: Dict[str, Vulnerability] = {}

    def register_vulnerability(self, vuln: Vulnerability):
        """Registers a new vulnerability definition."""
        if vuln.vuln_id in self._vulnerabilities:
            # Potentially log a warning for overwriting or raise an error
            print(f"Warning: Vulnerability ID '{vuln.vuln_id}' already registered. Overwriting.")
        self._vulnerabilities[vuln.vuln_id] = vuln

    def get_vulnerability(self, vuln_id: str) -> Optional[Vulnerability]:
        """Retrieves a vulnerability definition by its ID."""
        return self._vulnerabilities.get(vuln_id)

    def get_all_vulnerabilities(self) -> List[Vulnerability]:
        """Returns a list of all registered vulnerability definitions."""
        return list(self._vulnerabilities.values())

    def load_from_list(self, vuln_data_list: List[Dict[str, Any]]):
        """Loads multiple vulnerability definitions from a list of dictionaries."""
        for vuln_data in vuln_data_list:
            try:
                vuln = Vulnerability.from_dict(vuln_data)
                self.register_vulnerability(vuln)
            except Exception as e:
                print(f"Error loading vulnerability data: {vuln_data.get('vuln_id', 'Unknown ID')}. Error: {e}")

    def clear_registry(self):
        """Clears all vulnerabilities from the registry."""
        self._vulnerabilities.clear()

# --- Example Predefined Vulnerabilities (could be loaded from a JSON/YAML file later) ---
PREDEFINED_VULNERABILITIES_DATA = [
    {
        "vuln_id": "SQLi_WebApp_Login_001",
        "name": "SQL Injection in WebApp Login",
        "description": "A critical SQL injection vulnerability exists in the login form of the web application, allowing attackers to bypass authentication and potentially access sensitive data or execute arbitrary commands.",
        "severity": "Critical",
        "category": "Data Manipulation",
        "cvss_score": 9.8,
        "affected_components": ["WebApp v1.0 Login Module"],
        "mitre_attack_ids": ["T1190", "T1505.003"], # Exploit Public-Facing App, SQL Injection
        "patch_difficulty": 7,
        "exploit_difficulty": 4
    },
    {
        "vuln_id": "CVE-2023-0002_WebServer_RCE",
        "name": "Remote Code Execution in WebServer Service",
        "description": "A remote code execution vulnerability in the underlying web server software allows unauthenticated attackers to execute arbitrary code with system privileges.",
        "severity": "Critical",
        "category": "Code Execution",
        "cvss_score": 10.0,
        "affected_components": ["WebServerDaemon v2.1.3"],
        "mitre_attack_ids": ["T1190"],
        "patch_difficulty": 5,
        "exploit_difficulty": 3
    },
    {
        "vuln_id": "Misconf_SSH_WeakCreds_003",
        "name": "SSH Weak Credentials",
        "description": "The SSH service on the server is configured with weak or default credentials, allowing for easy brute-force attacks or unauthorized access.",
        "severity": "High",
        "category": "Access Control Bypass",
        "cvss_score": 7.5,
        "affected_components": ["OpenSSH Server (any version)"],
        "mitre_attack_ids": ["T1110.001", "T1078"], # Brute Force: Password Guessing, Valid Accounts
        "patch_difficulty": 3, # Easy to fix by changing password
        "exploit_difficulty": 2 # Easy to attempt brute force
    },
    {
        "vuln_id": "InfoLeak_WebServer_DirectoryListing_004",
        "name": "Directory Listing Enabled on Web Server",
        "description": "The web server has directory listing enabled, potentially exposing sensitive file names and directory structures.",
        "severity": "Medium",
        "category": "Information Disclosure",
        "cvss_score": 5.3,
        "affected_components": ["WebServerDaemon (any version)"],
        "mitre_attack_ids": ["T1083"], # File and Directory Discovery
        "patch_difficulty": 2,
        "exploit_difficulty": 1 # Easy to find if present
    }
]

# Global instance of the registry, to be used throughout the application
# This promotes a singleton-like pattern for vulnerability definitions.
# The StateManager or SimulationEngine will typically hold/initialize this.
# For now, defining it here for simplicity and ease of access.
# In a larger app, this might be dependency injected.
VULN_REGISTRY = VulnerabilityRegistry()
VULN_REGISTRY.load_from_list(PREDEFINED_VULNERABILITIES_DATA)


if __name__ == '__main__':
    print("--- Testing Vulnerability System ---")

    # Test getting a vulnerability
    sqli_vuln = VULN_REGISTRY.get_vulnerability("SQLi_WebApp_Login_001")
    if sqli_vuln:
        print(f"\nRetrieved: {sqli_vuln}")
        print(f"Serialized: {sqli_vuln.to_dict()}")
        assert sqli_vuln.severity == VulnerabilitySeverity.CRITICAL
        assert sqli_vuln.category == VulnerabilityCategory.DATA_MANIPULATION

    rce_vuln = VULN_REGISTRY.get_vulnerability("CVE-2023-0002_WebServer_RCE")
    if rce_vuln:
        print(f"\nRetrieved: {rce_vuln}")
        assert rce_vuln.mitre_attack_ids == ["T1190"]

    print("\n--- All Registered Vulnerabilities ---")
    for vuln_obj in VULN_REGISTRY.get_all_vulnerabilities():
        print(f"- {vuln_obj.vuln_id}: {vuln_obj.name} ({vuln_obj.severity.value})")

    # Test loading from a dictionary (simulating from_dict)
    test_data = {
        "vuln_id": "Test_Vuln_005",
        "name": "Test Vulnerability",
        "description": "A test vulnerability.",
        "severity": "Low", # Using string value for enum
        "category": "Other", # Using string value for enum
        "cvss_score": 3.0,
        "patch_difficulty": 1,
        "exploit_difficulty": 1
    }
    rehydrated_vuln = Vulnerability.from_dict(test_data)
    print(f"\nRehydrated from dict: {rehydrated_vuln}")
    assert rehydrated_vuln.severity == VulnerabilitySeverity.LOW

    # How Nodes might use this:
    # In network_elements.py, a Node's 'vulnerabilities' list would store vuln_ids (strings).
    # To get the full Vulnerability object:
    # node_vuln_ids = ["SQLi_WebApp_Login_001", "InfoLeak_WebServer_DirectoryListing_004"]
    # for vid in node_vuln_ids:
    #     vuln_object = VULN_REGISTRY.get_vulnerability(vid)
    #     if vuln_object:
    #         print(f"Node has vulnerability: {vuln_object.name}")

    print("\n--- Vulnerability System Test Complete ---")