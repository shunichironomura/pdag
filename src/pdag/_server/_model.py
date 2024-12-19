from typing import Annotated

from pydantic import BaseModel, Field
from pydantic_extra_types.color import Color


class ReactFlowNodePosition(BaseModel):
    x: float
    y: float


class ReactFlowNodeMeasured(BaseModel):
    width: int
    height: int


class ReactFlowValueNodeData(BaseModel):
    label: str
    is_complete: Annotated[bool, Field(alias="isComplete")]
    name: str
    value_type: Annotated[str, Field(alias="valuetype")]
    time_variable: bool


class ReactFlowValueNode(BaseModel):
    id: str
    type: str
    data: ReactFlowValueNodeData
    position: ReactFlowNodePosition
    measured: ReactFlowNodeMeasured
    selected: bool
    dragging: bool


class ReactFlowRelationshipNodeData(BaseModel):
    label: str
    is_intermediate: Annotated[bool, Field(alias="isIntermediate")]
    name: str
    function_body: Annotated[str, Field(alias="functionBody")]
    is_complete: Annotated[bool, Field(alias="isComplete")]


class ReactFlowRelationshipNode(BaseModel):
    id: str
    type: str
    data: ReactFlowRelationshipNodeData
    position: ReactFlowNodePosition
    measured: ReactFlowNodeMeasured
    selected: bool
    dragging: bool


class ReactFlowEdgeData(BaseModel):
    delay: bool


class ReactFlowEdgeMarker(BaseModel):
    type: str = "arrowclosed"
    color: Color = Color("#999")


class ReactFlowEdgeStyle(BaseModel):
    stroke: Color = Color("#999")


class ReactFlowEdge(BaseModel):
    id: str
    source: str
    target: str
    type: str = "floating"
    data: ReactFlowEdgeData
    animated: bool
    marker_end: Annotated[ReactFlowEdgeMarker, Field(alias="markerEnd")]
    style: ReactFlowEdgeStyle


class ReactFlowGraph(BaseModel):
    nodes: list[ReactFlowValueNode | ReactFlowRelationshipNode]
    edges: list[ReactFlowEdge]
