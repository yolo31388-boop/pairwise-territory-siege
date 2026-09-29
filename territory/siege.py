"""领地战与攻城系统"""
from dataclasses import dataclass, field

MIN_RESPAWN_DISTANCE = 10.0   # 复活点离城墙的最短距离
TAX_MIN, TAX_MAX = 0.05, 0.30  # 税率上下限
LAST_HIT_WEIGHT = 0.05        # 最后一击的少量权重
GUARDS_PER_LEVEL = 5          # 每级领地允许的守卫数

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
        self.attacker_spawn_distance: float = 20.0
        self.front_line_advance: float = 0.0  # 战线推进距离
        self.gates: dict[str, Gate] = {"left": Gate("left", 100, 100), "right": Gate("right", 100, 100)}
        self.tax_rate: float = 0.2
        self.guards: list = []
        self.max_guards: int = 0  # 0表示按领地等级计算
        self.territory_level: int = 1
        self.flag_progress: float = 0.0
        self.flag_decay_rate: float = 1.0
        self.battle_end_time: float = 0
        self.players_in_battle: set = set()
        self.damage_log: dict[str, float] = {}  # guild -> total damage
        self.last_hit_guild: str = ""

    def get_respawn_point(self, attacker_pos: tuple) -> tuple:
        # 复活点有最短距离限制，随战线推进而前移
        distance = max(MIN_RESPAWN_DISTANCE,
                       self.attacker_spawn_distance - self.front_line_advance)
        return (attacker_pos[0] + distance, attacker_pos[1])

    def damage_gate(self, side: str, dmg: float):
        # 左右扇独立计算血量，只开被打烂的那一侧
        gate = self.gates[side]
        gate.hp = max(0.0, gate.hp - dmg)
        if gate.hp <= 0:
            gate.open = True

    def set_tax(self, rate: float):
        # 税率限制在5%-30%
        self.tax_rate = max(TAX_MIN, min(TAX_MAX, rate))

    def siege_engine_damage(self, engine: SiegeEngine, target: str) -> float:
        # 攻城器械只对建筑和NPC造成伤害，对玩家无效
        if target == "player":
            return 0.0
        return engine.damage

    def record_damage(self, guild: str, dmg: float, is_last_hit: bool = False):
        self.damage_log[guild] = self.damage_log.get(guild, 0.0) + dmg
        if is_last_hit:
            self.last_hit_guild = guild

    def calculate_ownership(self) -> str:
        # 按伤害总量占比判定，最后一击只加少量权重
        if not self.damage_log:
            return ""
        total = sum(self.damage_log.values())
        def score(guild: str) -> float:
            s = self.damage_log[guild] / total if total > 0 else 0.0
            if guild == self.last_hit_guild:
                s += LAST_HIT_WEIGHT
            return s
        return max(self.damage_log, key=score)

    def add_guard(self, guard):
        # 守卫数量有上限，与领地等级挂钩
        cap = self.max_guards if self.max_guards > 0 else self.territory_level * GUARDS_PER_LEVEL
        if cap > 0 and len(self.guards) >= cap:
            return False
        self.guards.append(guard)
        return True

    def update_flag(self, attacker_present: bool, dt: float):
        if attacker_present:
            self.flag_progress += dt
        else:
            # 进攻方离开后按速率回退
            self.flag_progress = max(0.0, self.flag_progress - self.flag_decay_rate * dt)

    def end_battle(self):
        # 结束时间到后强制结算并传送所有玩家出战场
        self.battle_end_time = 0
        self.players_in_battle.clear()
