import gc
import unittest
import weakref
from pathlib import Path
from types import SimpleNamespace

import sc2reader
from sc2reader.engine.engine import GameEngine
from sc2reader.engine.plugins.context import ContextLoader
from sc2reader.events.game import (
    BasicCommandEvent,
    TargetUnitCommandEvent,
    UpdateTargetUnitCommandEvent,
)


class Player:
    def __init__(self, pid=1):
        self.pid = pid
        self.name = "Player"
        self.events = []


def command(event_type=TargetUnitCommandEvent, frame=1, pid=0, ability_link=1):
    data = {
        "flags": 0,
        "ability": {
            "ability_link": ability_link,
            "ability_command_index": 0,
            "ability_command_data": None,
        },
        "other_unit_tag": None,
        "data": ("TargetUnit", {"point": {}, "unit_tag": 1, "unit_link": 1}),
    }
    if event_type is BasicCommandEvent:
        data["data"] = ("None", None)
    return event_type(frame, pid, data)


def replay_with(events, players=1):
    people = [Player(pid + 1) for pid in range(players)]
    return SimpleNamespace(
        events=events,
        versions=(0, 5),
        build=98310,
        humans=people,
        human=dict(enumerate(people)),
        players=people,
        tracker_events=[object()],
        objects={1: object()},
        datapack=SimpleNamespace(
            abilities={
                0: SimpleNamespace(name="RightClick"),
                32: SimpleNamespace(name="Inject"),
            }
        ),
        marked_error=True,
    )


class ContextLifecycleTest(unittest.TestCase):
    def test_real_replay_can_be_collected_while_engine_is_reused(self):
        engine = GameEngine([ContextLoader()])
        fixture = (
            Path(__file__).resolve().parents[1]
            / "test_replays"
            / "5.0.0.80949"
            / "2020-07-28 - (T)Ocrucius VS (Z)Rairden.SC2Replay"
        )

        def analyze():
            replay = sc2reader.load_replay(str(fixture), load_map=False, engine=engine)
            event = next(e for e in replay.game_events if isinstance(e, TargetUnitCommandEvent))
            return weakref.ref(event), weakref.ref(event.player)

        event, player = analyze()
        gc.collect()
        self.assertIsNone(event())
        self.assertIsNone(player())

    def test_engine_does_not_retain_released_replay_events(self):
        engine = GameEngine([ContextLoader()])

        def analyze():
            event = command()
            replay = replay_with([event])
            engine.run(replay)
            return weakref.ref(event), weakref.ref(replay.players[0])

        for _ in range(2):
            event, player = analyze()
            gc.collect()
            self.assertIsNone(event())
            self.assertIsNone(player())

    def test_update_keeps_ability_and_other_players_are_independent(self):
        target = command()
        update = command(UpdateTargetUnitCommandEvent, frame=3, ability_link=0)
        other_player = command(UpdateTargetUnitCommandEvent, frame=2, pid=1, ability_link=0)
        replay = replay_with([target, other_player, update], players=2)
        GameEngine([ContextLoader()]).run(replay)
        self.assertEqual(update.ability_name, "Inject")
        self.assertEqual(other_player.ability_name, "RightClick")

    def test_plugins_can_change_the_previous_event_ability(self):
        class RenameAbility:
            name = "RenameAbility"

            def handleTargetUnitCommandEvent(self, event, replay):
                event.ability_name = "Renamed"

        target = command()
        update = command(UpdateTargetUnitCommandEvent, frame=2, ability_link=0)
        replay = replay_with([target, update])
        GameEngine([ContextLoader(), RenameAbility()]).run(replay)
        self.assertEqual(update.ability_name, "Renamed")

    def test_end_game_plugins_can_emit_an_update(self):
        class EmitUpdate:
            name = "EmitUpdate"

            def handleEndGame(self, event, replay):
                yield command(UpdateTargetUnitCommandEvent, frame=2, ability_link=0)

        replay = replay_with([command()])
        GameEngine([ContextLoader(), EmitUpdate()]).run(replay)
        self.assertEqual(len(replay.players[0].events), 2)
        self.assertIsInstance(replay.players[0].events[-1], UpdateTargetUnitCommandEvent)
        self.assertEqual(replay.players[0].events[-1].ability_name, "Inject")

    def test_missing_ability_invalidates_previous_command(self):
        unknown = command(BasicCommandEvent, frame=2, ability_link=99)
        update = command(UpdateTargetUnitCommandEvent, frame=3, ability_link=0)
        replay = replay_with([command(), unknown, update])
        GameEngine([ContextLoader()]).run(replay)
        self.assertEqual(update.ability_name, "RightClick")

    def test_replay_start_clears_previous_ability(self):
        engine = GameEngine([ContextLoader()])
        engine.run(replay_with([command()]))
        update = command(UpdateTargetUnitCommandEvent, ability_link=0)
        engine.run(replay_with([update]))
        self.assertEqual(update.ability_name, "RightClick")

    def test_loader_does_not_retain_events_when_context_loading_fails(self):
        engine = GameEngine([ContextLoader()])

        def analyze():
            event = command()
            replay = replay_with([event])
            # Target context stores the command before resolving its target.
            # An invalid datapack therefore exercises an error after caching.
            replay.objects.clear()
            with self.assertRaises(AttributeError):
                engine.run(replay)
            return weakref.ref(event), weakref.ref(replay.players[0])

        event, player = analyze()
        gc.collect()
        self.assertIsNone(event())
        self.assertIsNone(player())


if __name__ == "__main__":
    unittest.main()
