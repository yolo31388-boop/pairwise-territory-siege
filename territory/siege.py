"""领地战与攻城系统"""
from dataclasses import dataclass

MIN_TAX_RATE = 0.05
MAX_TAX_RATE = 0.30

MIN_RESPAWN_DISTANCE = 20.0
SPAWN_RETREAT_PER_PROGRESS = 30.0

LAST_HIT_BONUS_RATIO = 0.05

GUARDS_PER_TERRITORY_LEVEL = 10

PLAYER_TARGETS = frozenset({"player"})
ENGINE_TARGETS = frozenset({"building", "npc"})


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
    target_type: str = "building"  # building/npc：只对建筑和NPC生效


class Siege:
    def __init__(self):
        # 攻城方复活点：距城墙的最短距离，并随战线推进而后撤
        self.attacker_spawn_distance: float = MIN_RESPAWN_DISTANCE
        self.front_progress: float = 0.0  # 战线推进程度 0.0~1.0
        # 城门：左右扇独立血量，只开被打烂的那一侧
        self.gates: dict[str, Gate] = {
            "left": Gate("left", 100.0, 100.0),
            "right": Gate("right", 100.0, 100.0),
        }
        # 税率限制在 5%~30%
        self.tax_rate: float = 0.2
        # NPC守卫：上限与领地等级挂钩
        self.territory_level: int = 1
        self.max_guards: int = GUARDS_PER_TERRITORY_LEVEL
        self.guards: list = []
        # 战旗：进攻方离开后按速率回退
        self.flag_progress: float = 0.0
        self.flag_decay_rate: float = 1.0
        # 战场时间与在场玩家
        self.battle_end_time: float = 0
        self.battle_settled: bool = False
        self.players_in_battle: set = set()
        self.teleported_out: set = set()
        self.exit_point: tuple = (0, 0)
        # 领地归属：按各公会伤害总量占比判定，最后一击只加少量权重
        self.damage_log: dict[str, float] = {}
        self.last_hit_guild: str | None = None

    @property
    def total_gate_hp(self) -> float:
        return sum(gate.hp for gate in self.gates.values())

    def update_front(self, progress: float):
        """战线推进：越往里打，攻城方复活点后撤得越远。"""
        self.front_progress = min(1.0, max(0.0, progress))
        retreated = MIN_RESPAWN_DISTANCE + SPAWN_RETREAT_PER_PROGRESS * self.front_progress
        if self.attacker_spawn_distance < retreated:
            self.attacker_spawn_distance = retreated

    def get_respawn_point(self, attacker_pos: tuple) -> tuple:
        # 保证复活点与城墙保持最短距离，且随战线推进后撤
        distance = max(
            self.attacker_spawn_distance,
            MIN_RESPAWN_DISTANCE + SPAWN_RETREAT_PER_PROGRESS * self.front_progress,
        )
        return (attacker_pos[0] + distance, attacker_pos[1])

    def damage_gate(self, side: str, dmg: float):
        # 左右扇独立计算血量，只开被打烂的那一侧
        gate = self.gates[side]
        if gate.open or dmg <= 0:
            return
        gate.hp = max(0.0, gate.hp - dmg)
        if gate.hp <= 0:
            gate.open = True

    def set_tax(self, rate: float):
        # 税率钳制在 [5%, 30%]
        self.tax_rate = min(MAX_TAX_RATE, max(MIN_TAX_RATE, rate))

    def siege_engine_damage(self, engine: SiegeEngine, target: str) -> float:
        # 攻城器械只伤建筑和NPC，对玩家无效
        if target in PLAYER_TARGETS:
            return 0.0
        if target in ENGINE_TARGETS:
            return engine.damage
        return 0.0

    def record_damage(self, guild: str, dmg: float, last_hit: bool = False):
        self.damage_log[guild] = self.damage_log.get(guild, 0.0) + dmg
        if last_hit:
            self.last_hit_guild = guild

    def calculate_ownership(self) -> str:
        # 按伤害总量占比判定，最后一击仅额外加少量权重
        if not self.damage_log:
            return ""
        total_damage = sum(self.damage_log.values())
        last_hit_bonus = total_damage * LAST_HIT_BONUS_RATIO
        weighted = {
            guild: damage + (last_hit_bonus if guild == self.last_hit_guild else 0.0)
            for guild, damage in self.damage_log.items()
        }
        return max(weighted, key=weighted.get)

    def set_territory_level(self, level: int):
        self.territory_level = max(1, int(level))
        self.max_guards = self.territory_level * GUARDS_PER_TERRITORY_LEVEL
        if len(self.guards) > self.max_guards:
            del self.guards[self.max_guards:]

    def add_guard(self, guard) -> bool:
        # 守卫数量有上限，且与领地等级挂钩
        if len(self.guards) >= self.max_guards:
            return False
        self.guards.append(guard)
        return True

    def update_flag(self, attacker_present: bool, dt: float):
        # 进攻方在场则推进占领进度，离开后按速率回退
        if attacker_present:
            self.flag_progress = min(100.0, self.flag_progress + dt)
        else:
            self.flag_progress = max(0.0, self.flag_progress - self.flag_decay_rate * dt)

    def teleport_player(self, player, point: tuple | None = None):
        self.teleported_out.add(player)
        return self.exit_point if point is None else point

    def end_battle(self):
        # 时间到后强制结算，并把所有玩家传送出战场
        self.battle_settled = True
        self.battle_end_time = 0
        for player in list(self.players_in_battle):
            self.teleport_player(player, self.exit_point)
        self.players_in_battle.clear()
