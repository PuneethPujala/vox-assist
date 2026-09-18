import pytest
import asyncio
import sys
import os

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)
sys.path.insert(0, os.path.join(backend_dir, "engine"))

from services.generation_service import GenerationService

def test_generation_service_architectural_payload():
    async def _run():
        service = GenerationService()
        result = await service.generate_layout("Modern 2 bedroom house with kitchen and dining")
        
        assert result["success"] is True
        assert "architectural_check" in result
        arch = result["architectural_check"]
        assert arch is not None
        assert "feasibility_score" in arch
        assert "checks_passed" in arch
        assert "checks_total" in arch
        assert arch["checks_total"] == 7
        assert len(arch["checks"]) == 7
        
        # Verify each candidate in the Best-of-3 list also has architectural_check
        assert "candidates" in result
        assert len(result["candidates"]) > 0
        for cand in result["candidates"]:
            assert "architectural_check" in cand
            assert cand["architectural_check"]["checks_total"] == 7

    asyncio.run(_run())
