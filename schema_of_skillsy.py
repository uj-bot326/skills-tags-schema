from mongoengine import (
    Document, EmbeddedDocument, connect,
    StringField, IntField, BooleanField,
    ListField, DictField, EmbeddedDocumentField
)
from datetime import datetime
connect("skills_db")  # connect to your MongoDB
class EnrichedData(EmbeddedDocument):
    """Enriched metadata sub-document."""
    skill_name  = StringField(required=True)
    description = StringField(default=None)
    type        = StringField(default=None)  # "technical", "soft", "domain"
class Skill(Document):
    """Generic Skill document schema."""
    name         = StringField(required=True, unique=True)
    type         = StringField(required=True)   # e.g. "SKILL", "TOOL"
    search_names = ListField(StringField(), default=list)
    synonyms     = ListField(StringField(), default=list)
    count        = IntField(default=0)
    description  = StringField(default=None)
    data         = DictField(default=dict)       # flexible extra metadata
    deleted      = BooleanField(default=False)   # soft delete flag
    children     = ListField(DictField(), default=list)
    links        = ListField(DictField(), default=list)
    enriched     = BooleanField(default=False)
    verify       = BooleanField(default=False)
    enriched_data = EmbeddedDocumentField(EnrichedData, default=None)
    created_at   = StringField(default=lambda: datetime.utcnow().isoformat())
    updated_at   = StringField(default=lambda: datetime.utcnow().isoformat())
    meta = {
        "collection": "skills",
        "indexes": [
            { "fields": ["name"],                    "unique": True },
            { "fields": ["type", "deleted"] },
            { "fields": ["enriched"] },
            { "fields": ["enriched_data.type"] },
        ]
    }
