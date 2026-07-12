"""Tests for the Prefect data model."""
import pytest
from models.enums import Role, Form, Weekday, SchoolRules
from models.prefect import Prefect


class TestPrefectConstruction:
    """Test basic Prefect construction and validation."""

    def test_valid_study_prefect(self):
        p = Prefect(
            name="CHAN Tai Man",
            form=Form.F4,
            class_name="4A",
            role=Role.STUDY_PREFECT,
            available=[Weekday.MON, Weekday.WED, Weekday.FRI],
        )
        assert p.name == "CHAN Tai Man"
        assert p.is_study_prefect
        assert not p.is_ahp
        assert not p.is_head
        assert p.can_do_room_duty
        assert p.history_weight == 0.0

    def test_valid_ahp(self):
        p = Prefect(
            name="WONG Siu Ming",
            form=Form.F5,
            class_name="5B",
            role=Role.ASSISTANT_HEAD_PREFECT,
            available=[Weekday.MON, Weekday.TUE, Weekday.WED, Weekday.THU, Weekday.FRI],
        )
        assert p.is_ahp
        assert p.is_leader
        assert not p.can_do_room_duty

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="Name is required"):
            Prefect(name="", form=Form.F4, role=Role.STUDY_PREFECT)

    def test_f3_ahp_raises(self):
        """F.3 students cannot be AHP."""
        with pytest.raises(ValueError, match="AHP must be F.4 or F.5"):
            Prefect(name="Test", form=Form.F3, role=Role.ASSISTANT_HEAD_PREFECT)

    def test_negative_history_weight_raises(self):
        with pytest.raises(ValueError):
            Prefect(name="Test", form=Form.F4, history_weight=-1.0)


class TestPrefectProperties:
    """Test computed properties."""

    def test_is_available_on(self):
        p = Prefect(name="Test", form=Form.F4, available=[Weekday.MON, Weekday.FRI])
        assert p.is_available_on(Weekday.MON)
        assert not p.is_available_on(Weekday.TUE)

    def test_add_load(self):
        p = Prefect(name="Test", form=Form.F4, history_weight=3.0)
        p.add_load(2.0)
        assert p.history_weight == 5.0

    def test_add_load_negative_raises(self):
        p = Prefect(name="Test", form=Form.F4)
        with pytest.raises(ValueError, match="non-negative"):
            p.add_load(-1.0)

    def test_apply_multiplier(self):
        p = Prefect(name="Test", form=Form.F4, history_weight=10.0)
        p.apply_multiplier(1.5)
        assert p.history_weight == 15.0

    def test_multiplier_out_of_range_raises(self):
        p = Prefect(name="Test", form=Form.F4)
        with pytest.raises(ValueError, match="Multiplier must be between"):
            p.apply_multiplier(3.0)


class TestPrefectSerialization:
    """Test to_dict and from_row round-trip."""

    def test_to_dict_roundtrip(self):
        p = Prefect(
            name="LI Chuang Jie",
            name_zh="Li Chuang Jie",
            form=Form.F5,
            class_name="5A",
            role=Role.HEAD_STUDY_PREFECT,
            available=[Weekday.MON, Weekday.TUE],
            history_weight=3.5,
            remarks="Head Prefect",
        )
        d = p.to_dict()
        p2 = Prefect.from_row(d)
        assert p2.name == p.name
        assert p2.role == p.role
        assert p2.form == p.form
        assert p2.history_weight == p.history_weight
        assert p2.available == p.available
