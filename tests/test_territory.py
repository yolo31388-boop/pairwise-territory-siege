"""领地战与攻城系统 - 红态测试"""
import pytest
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from territory.siege import Siege, Gate, SiegeEngine

class TestRespawnDistance:
    def test_respawn_has_min_distance(self):
        s = Siege()
        s.attacker_spawn_distance = 10.0
        pos = s.get_respawn_point((0, 0))
        assert abs(pos[0]) >= 10  # bug1: 只有3

class TestGateIndependent:
    def test_left_gate_damage_doesnt_open_right(self):
        s = Siege()
        s.damage_gate("left", 150)  # 打烂左边
        assert s.gates["left"].open == True
        assert s.gates["right"].open == False  # bug2: 也开了

class TestTaxCap:
    def test_tax_has_upper_bound(self):
        s = Siege()
        s.set_tax(1.0)
        assert s.tax_rate <= 0.3  # bug3: 1.0

class TestSiegeEngineTarget:
    def test_engine_doesnt_damage_players(self):
        s = Siege()
        engine = SiegeEngine("e1", 100, target_type="building")
        # 对玩家应该减伤或无效
        dmg = s.siege_engine_damage(engine, "player")
        assert dmg < 100  # bug4: 100全额

class TestOwnershipByDamage:
    def test_ownership_by_total_damage_not_last_hit(self):
        s = Siege()
        s.damage_log["guild_A"] = 900
        s.damage_log["guild_B"] = 100
        # guild_A打了90%，应该归属A
        assert s.calculate_ownership() == "guild_A"  # bug5: 可能看最后一击

class TestGuardCap:
    def test_guard_count_has_cap(self):
        s = Siege()
        s.max_guards = 10
        for i in range(15):
            s.add_guard(f"guard_{i}")
        assert len(s.guards) <= 10  # bug6: 15个

class TestFlagDecay:
    def test_flag_decays_when_attacker_leaves(self):
        s = Siege()
        s.flag_progress = 50.0
        s.flag_decay_rate = 1.0
        s.update_flag(False, 10.0)  # 进攻方离开10秒
        assert s.flag_progress < 50.0  # bug7: 还是50

class TestBattleEndTeleport:
    def test_battle_end_clears_players(self):
        s = Siege()
        s.players_in_battle = {"p1", "p2", "p3"}
        s.end_battle()
        assert len(s.players_in_battle) == 0  # bug8: 还是3
