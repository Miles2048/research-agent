"""Data models for database format module."""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime

@dataclass
class Reference:
    """Reference data model matching database schema."""
    id: int
    reference_type: str = '未分类'
    reference_url: str = ''
    reference_title: str = ''
    reference_content: Optional[str] = None
    publisher: Optional[str] = None
    credibility: Optional[int] = 2
    related_assessment: Optional[float] = 0.80
    credibility_assessment: Optional[str] = None
    related_assessment_text: Optional[str] = None
    reference_create_time: Optional[datetime] = None
    reference_update_time: Optional[datetime] = None
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'Reference':
        """Create Reference from database row."""
        # Assuming the row contains: id, reference_type, reference_url, reference_title, 
        # reference_content, publisher, credibility, related_assessment,
        # credibility_assessment, related_assessment_text
        return cls(
            id=row[0],
            reference_type=row[1] or '未分类',
            reference_url=row[2] or '',
            reference_title=row[3] or '',
            reference_content=row[4],
            publisher=row[5],
            credibility=row[6] or 2,
            related_assessment=row[7] or 0.80,
            credibility_assessment=row[8],
            related_assessment_text=row[9]
        )
    
    def needs_evaluation(self) -> bool:
        """Check if reference needs evaluation."""
        return (
            self.reference_type == '未分类' or
            self.credibility == 2 or  # Default value
            self.related_assessment == 0.80 or  # Default value
            not self.credibility_assessment or
            not self.related_assessment_text
        )

@dataclass
class EvaluationResult:
    """Result of LLM evaluation for a reference."""
    reference_type: str
    credibility: int
    credibility_assessment: str
    related_assessment: float
    related_assessment_text: str
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database update."""
        return {
            'reference_type': self.reference_type,
            'credibility': self.credibility,
            'credibility_assessment': self.credibility_assessment,
            'related_assessment': self.related_assessment,
            'related_assessment_text': self.related_assessment_text
        }
    
    def validate(self) -> bool:
        """Validate evaluation result."""
        return (
            self.reference_type in [
                "用户输入", "行业研究报告", "同行评审的学术出版物",
                "竞对公司网站和产品页面", "政策与准入数据", "社交媒体和公共论坛"
            ] and
            1 <= self.credibility <= 3 and
            0.0 <= self.related_assessment <= 1.0 and
            len(self.credibility_assessment) > 0 and
            len(self.related_assessment_text) > 0
        )

@dataclass
class BatchResult:
    """Result of batch processing."""
    total_processed: int = 0
    successful: int = 0
    failed: int = 0
    errors: list = field(default_factory=list)
    
    def add_success(self):
        """Record successful processing."""
        self.total_processed += 1
        self.successful += 1
    
    def add_failure(self, error: str):
        """Record failed processing."""
        self.total_processed += 1
        self.failed += 1
        self.errors.append(error)
    
    def summary(self) -> str:
        """Get summary of batch processing."""
        return (
            f"Batch processing completed:\n"
            f"Total processed: {self.total_processed}\n"
            f"Successful: {self.successful}\n"
            f"Failed: {self.failed}\n"
            f"Success rate: {self.successful/self.total_processed*100:.1f}%" if self.total_processed > 0 else "No items processed"
        )