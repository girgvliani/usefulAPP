"""Explicit conversion from service-layer result dicts (which hold live ORM
objects) into Pydantic response schemas, so we never hand a raw ORM instance
to FastAPI's response serializer."""

from app.schemas import LifeAreaOut, XpResult


def xp_result_to_schema(result: dict | None) -> XpResult | None:
    if result is None:
        return None
    return XpResult(
        area=LifeAreaOut.model_validate(result["area"]),
        leveled_up=result["leveled_up"],
        achievement=result["achievement"],
    )
