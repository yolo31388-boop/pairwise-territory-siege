"""领地战与攻城系统 - 含8个bug"""
from dataclasses import dataclass, field

@dataclass
class Gate:
    side: str  # left/right
    hp: float
    max_hp: float
    open: bool = False

@dataclass
class SiegeEngine:
    eid: str
    damage: float
    target_type: str = "all"  # bug4: 对玩家也生效

class Siege:
    def __init__(self):
        self.attacker_spawn_distance: float = 5.0  # bug1: 太近
        self.gates: dict[str, Gate] = {"left": Gate("left", 100, 100), "right": Gate("right", 100, 100)}
        self.total_gate_hp: float = 200  # bug2: 不区分左右扇
        self.tax_rate: float = 0.2
        self.guards: list = []
        self.max_guards: int = 0  # bug6: 无上限
        self.flag_progress: float = 0.0
        self.flag_decay_rate: float = 0.0  # bug7: 不回退
        self.battle_end_time: float = 0
        self.players_in_battle: set = set()
        self.damage_log: dict[str, float] = {}  # guild -> total damage

    def get_respawn_point(self, attacker_pos: tuple) -> tuple:
        # bug1: 复活点离城墙太近
        return (attacker_pos[0] + 3, attacker_pos[1])  # 只加3码

    def damage_gate(self, side: str, dmg: float):
        # bug2: 打一边两边都开
        self.total_gate_hp -= dmg
        if self.total_gate_hp <= 0:
            self.gates["left"].open = True
            self.gates["right"].open = True

    def set_tax(self, rate: float):
        # bug3: 税率无上限
        self.tax_rate = rate

    def siege_engine_damage(self, engine: SiegeEngine, target: str) -> float:
        # bug4: 对玩家也造成伤害
        return engine.damage

    def calculate_ownership(self) -> str:
        # bug5: 只看最后一击
        if not self.damage_log:
            return ""
        return max(self.damage_log, key=self.damage_log.get)

    def add_guard(self, guard):
        # bug6: 守卫数量无上限
        self.guards.append(guard)

    def update_flag(self, attacker_present: bool, dt: float):
        # bug7: 进攻方离开后不回退
        if attacker_present:
            self.flag_progress += dt
        # 没有else回退

    def end_battle(self):
        # bug8: 结束后不强制传送玩家
        self.battle_end_time = 0
        # players_in_battle没清空
