from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KULMSModel(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

