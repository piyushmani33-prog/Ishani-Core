"""
Tests for the Unified Brain Registry module.

Verifies:
- All required brains are registered
- Each brain has mandatory fields
- Hierarchy tiers are present and non-empty
- Brain IDs are unique
- Role mappings are present
"""

import os
import sys

BACKEND_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "techbuzz-full",
    "techbuzz-full",
    "backend_python",
)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


def _import_registry():
    import unified_brain_registry as ubr  # noqa: PLC0415
    return ubr


# ---------------------------------------------------------------------------
# File existence
# ---------------------------------------------------------------------------

class TestBrainRegistryFile:
    def test_file_exists(self):
        path = os.path.join(BACKEND_DIR, "unified_brain_registry.py")
        assert os.path.isfile(path), "unified_brain_registry.py must exist"

    def test_file_valid_python(self):
        path = os.path.join(BACKEND_DIR, "unified_brain_registry.py")
        with open(path, "r") as fh:
            source = fh.read()
        compile(source, path, "exec")


# ---------------------------------------------------------------------------
# Registry content
# ---------------------------------------------------------------------------

class TestBrainRegistryContent:
    REQUIRED_BRAIN_FIELDS = [
        "id",
        "purpose",
        "tier",
        "layer_label",
        "input_types",
        "output_types",
        "allowed_tools",
        "fallback_strategy",
        "enabled",
        "health_status",
        "fallback_active",
        "last_error",
        "ready_for_user",
        "ready_for_automation",
        "checked_at",
    ]

    CRITICAL_BRAINS = [
        "mother_brain",
        "recruitment_secretary",
        "public_agent",
        "tool_ats_kanban",
        "voice_runtime",
    ]

    def test_get_all_brains_returns_list(self):
        ubr = _import_registry()
        brains = ubr.get_all_brains()
        assert isinstance(brains, list)
        assert len(brains) > 0

    def test_brain_ids_are_unique(self):
        ubr = _import_registry()
        brains = ubr.get_all_brains()
        ids = [b["id"] for b in brains]
        assert len(ids) == len(set(ids)), "Brain IDs must be unique"

    def test_each_brain_has_required_fields(self):
        ubr = _import_registry()
        brains = ubr.get_all_brains()
        for brain in brains:
            for field in self.REQUIRED_BRAIN_FIELDS:
                assert field in brain, f"Brain '{brain.get('id')}' missing field '{field}'"

    def test_critical_brains_present(self):
        ubr = _import_registry()
        brains = ubr.get_all_brains()
        ids = {b["id"] for b in brains}
        for brain_id in self.CRITICAL_BRAINS:
            assert brain_id in ids, f"Critical brain '{brain_id}' missing from registry"

    def test_tier_values_are_valid(self):
        ubr = _import_registry()
        brains = ubr.get_all_brains()
        for brain in brains:
            assert isinstance(brain["tier"], int), f"Tier must be int for brain '{brain['id']}'"
            assert 1 <= brain["tier"] <= 6, f"Tier out of range for brain '{brain['id']}'"

    def test_get_brain_by_id(self):
        ubr = _import_registry()
        brain = ubr.get_brain("mother_brain")
        assert brain is not None
        assert brain["id"] == "mother_brain"
        assert brain["tier"] == 1

    def test_get_brain_unknown_id_returns_none(self):
        ubr = _import_registry()
        assert ubr.get_brain("does_not_exist_xyz") is None

    def test_get_brains_by_tier(self):
        ubr = _import_registry()
        tier1 = ubr.get_brains_by_tier(1)
        assert len(tier1) >= 1, "Tier 1 must contain at least mother_brain"
        assert any(b["id"] == "mother_brain" for b in tier1)

    def test_mother_brain_is_tier_1(self):
        ubr = _import_registry()
        brain = ubr.get_brain("mother_brain")
        assert brain["tier"] == 1, "mother_brain must be tier 1"


# ---------------------------------------------------------------------------
# Hierarchy
# ---------------------------------------------------------------------------

class TestBrainHierarchy:
    def test_hierarchy_returns_tiers(self):
        ubr = _import_registry()
        hierarchy = ubr.get_hierarchy()
        assert isinstance(hierarchy, list)
        assert len(hierarchy) >= 4, "Hierarchy must have at least 4 tiers"

    def test_hierarchy_tier_fields(self):
        ubr = _import_registry()
        hierarchy = ubr.get_hierarchy()
        for tier in hierarchy:
            assert "tier" in tier
            assert "label" in tier
            assert "brain_count" in tier
            assert "brains" in tier

    def test_hierarchy_tier_1_has_mother_brain(self):
        ubr = _import_registry()
        hierarchy = ubr.get_hierarchy()
        tier1 = next((t for t in hierarchy if t["tier"] == 1), None)
        assert tier1 is not None
        brain_ids = [b["id"] for b in tier1["brains"]]
        assert "mother_brain" in brain_ids
