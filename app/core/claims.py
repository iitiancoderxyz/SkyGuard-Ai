"""
TRUST-TWIN Core Claims and Disclaimers
Authoritative single source for scope, limitations, and standard disclaimers.
Principle P9 / Invariant INV-13.
"""

PROJECT_NAME = "TRUST-TWIN"
PROJECT_FULL_NAME = "Quarantine-Gated Sequential Evidence Monitor for AWS"
PROJECT_CODE = "SIH26073"

# Scope constants
ALLOWED_METEOROLOGICAL_INPUTS = (
    "temperature",
    "pressure",
    "relative_humidity",
)

DISCLAIMER_EVALUATION = (
    "Evaluation conducted on anomaly-injected and synthetic/historical surrogate data. "
    "Results reflect tested benchmark scenarios."
)

DISCLAIMER_HEALTH = (
    "Sensor health status is a longitudinal empirical indicator and not a physical sensor warranty."
)

DISCLAIMER_DEGRADATION = (
    "Degradation indicator reflects persistent baseline divergence trends and does not predict an exact remaining useful life or failure date."
)

DISCLAIMER_MAINTENANCE = (
    "Maintenance indication is an operational recommendation for sensor inspection and verification, not an automated physical repair guarantee."
)

DISCLAIMER_CALIBRATION = (
    "Confidence scores are empirical probabilities calibrated via isotonic regression on validation splits."
)

DISCLAIMER_NETWORK_CONTEXT = (
    "Network context provides coincident anomaly context from neighboring stations when geometry and latency permit; "
    "it does not model dynamic atmospheric front propagation."
)

DISCLAIMER_CORRECTION = (
    "Estimated replacement values are generated separately from raw observations for exploratory use. "
    "Raw observations are never overwritten or mutated."
)

BANNED_PHRASES = [
    "100% accuracy",
    "zero false alarms",
    "perfect detection",
    "guaranteed maintenance",
    "exact failure date",
    "failsafe",
]
