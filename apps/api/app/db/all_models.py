"""Import every ORM model so `Base.metadata` is fully populated.

Alembic's `env.py` and anything calling `Base.metadata.create_all()` must
import this module first — SQLAlchemy only knows about a model once its
module has executed.
"""

from app.modules.admin.models import AuditLog  # noqa: F401
from app.modules.companies.models import Company, EntityClaim  # noqa: F401
from app.modules.postings.models import JobPosting  # noqa: F401
from app.modules.recruiters.models import Recruiter  # noqa: F401
from app.modules.reports.models import Report, ReportEvidence  # noqa: F401
from app.modules.reviews.models import Review, ReviewVote  # noqa: F401
from app.modules.users.models import Notification, RefreshToken, User  # noqa: F401
from app.modules.verification.models import (  # noqa: F401
    ScoringConfig,
    Verification,
    VerificationSignal,
)
