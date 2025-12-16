import os
import yaml
import logging
from infrastructure.security.command_security import CommandSecurityChecker

logger = logging.getLogger(__name__)

RULES_DIR = os.path.join(os.path.dirname(__file__), "../rules/node")

results = []
checker = CommandSecurityChecker()

for fname in os.listdir(RULES_DIR):
    if not fname.endswith(".yaml"):
        continue
    path = os.path.join(RULES_DIR, fname)
    with open(path, "r", encoding="utf-8") as f:
        rule = yaml.safe_load(f)
    # Compatibility with different formats
    try:
        cmd = rule["config"]["execution"]["command"]
    except Exception:
        continue
    is_safe, risk, desc = checker.check_command_security(cmd)
    results.append(
        {
            "file": fname,
            "command": cmd,
            "is_safe": is_safe,
            "risk": str(risk),
            "desc": desc,
        }
    )

logger.info("Node rules command security check results:")
for r in results:
    logger.info(
        f"{r['file']}: {r['command']} => {'Safe' if r['is_safe'] else 'Forbidden'} | Risk: {r['risk']} | {r['desc']}"
    )
