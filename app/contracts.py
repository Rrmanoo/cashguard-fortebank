"""Public jury contract, independent of internal visual annotation schemas."""
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator

class Submission(BaseModel):
    job_id:str
    status:Literal['processing']

class EvidenceFrame(BaseModel):
    timestamp_sec:float=Field(ge=0,allow_inf_nan=False)
    image_base64:str=Field(description='JPEG bytes encoded as base64, without a data URL prefix')

class Violation(BaseModel):
    model_config=ConfigDict(extra='allow')
    type:str
    timecode_sec:float=Field(ge=0,allow_inf_nan=False)
    description:str
    evidence_frames:list[EvidenceFrame]=Field(min_length=1,max_length=3)

class JobStatus(BaseModel):
    model_config=ConfigDict(extra='allow')
    job_id:str
    status:Literal['processing','done','failed']
    stage:str|None=None
    verdict:Literal['violation','no_violation']|None=None
    violations:list[Violation]|None=None
    error:str|None=None

    @model_validator(mode='after')
    def completed_contract(self):
        if self.status=='done':
            if self.verdict is None or self.violations is None:
                raise ValueError('Completed jobs require verdict and violations')
            if (self.verdict=='violation')!=bool(self.violations):
                raise ValueError('Verdict and findings disagree')
        return self
