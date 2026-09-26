"""HTTP surface: health, wire panels, market quotes, and trade headlines."""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from oriel_server import __version__
from oriel_server.brief.selection import BriefStore
from oriel_server.config import Config, load_config
from datetime import datetime, timezone

from oriel_server.markets.poller import MarketPoller
from oriel_server.recommendations.service import Recommendations
from oriel_server.sports.news import SidelinePoller
from oriel_server.sports.poller import SportsPoller
from oriel_server.trade.poller import TradePoller
from oriel_server.weather.poller import WeatherPoller
from oriel_server.wires.catalog import find_repo_root
from oriel_server.wires.poller import WirePoller


class HomePlaceStatus(BaseModel):
    id: str
    name: str
    coordinates_set: bool


class BayPin(BaseModel):
    bay_id: str


class DeskDismiss(BaseModel):
    desk_id: str


class PlayerCommand(BaseModel):
    player_id: str


class ScoringCommand(BaseModel):
    scoring: str


class FollowCommand(BaseModel):
    competition_id: str
    follow: bool


class SportFocus(BaseModel):
    sport: str
    follow: bool


class BriefChoice(BaseModel):
    slot: str
    id: str = ""


class Health(BaseModel):
    status: str
    service: str
    version: str
    bind: str
    home_place: HomePlaceStatus


def create_app(
    config: Config | None = None,
    *,
    poller: WirePoller | None = None,
    market_poller: MarketPoller | None = None,
    trade_poller: TradePoller | None = None,
    weather_poller: WeatherPoller | None = None,
    sports_poller: SportsPoller | None = None,
    sideline_poller: SidelinePoller | None = None,
    brief: BriefStore | None = None,
) -> FastAPI:
    cfg = config if config is not None else load_config()
    root = None
    needs_root = (
        (poller is None and cfg.wires.enabled)
        or (market_poller is None and cfg.markets.enabled)
        or (trade_poller is None and cfg.trade.enabled)
        or (weather_poller is None and cfg.weather.enabled)
        or (sports_poller is None and cfg.sports.enabled)
    )
    if needs_root:
        root = find_repo_root()
    if poller is None and cfg.wires.enabled:
        assert root is not None
        poller = WirePoller(
            root / "catalog" / "outlets",
            stale_after_seconds=cfg.wires.stale_after_seconds,
            state_path=root / "server" / "state" / "wires.json",
        )
    if market_poller is None and cfg.markets.enabled:
        assert root is not None
        market_poller = MarketPoller(
            root / "catalog" / "markets",
            stale_after_seconds=cfg.markets.stale_after_seconds,
            state_path=root / "server" / "state" / "markets.json",
        )
    if trade_poller is None and cfg.trade.enabled:
        assert root is not None
        trade_poller = TradePoller(
            root / "catalog" / "trade",
            stale_after_seconds=cfg.trade.stale_after_seconds,
            state_path=root / "server" / "state" / "trade.json",
        )
    if weather_poller is None and cfg.weather.enabled:
        assert root is not None
        weather_poller = WeatherPoller(
            root / "catalog" / "weather",
            root / "catalog" / "weather-news",
            cfg.home_place,
            stale_after_seconds=cfg.weather.stale_after_seconds,
            state_path=root / "server" / "state" / "weather.json",
        )
    if sports_poller is None and cfg.sports.enabled:
        assert root is not None
        sports_poller = SportsPoller(
            root / "catalog" / "sports",
            stale_after_seconds=cfg.sports.stale_after_seconds,
            state_path=root / "server" / "state" / "sports.json",
        )
    if sideline_poller is None and cfg.sports.enabled:
        assert root is not None
        sideline_poller = SidelinePoller(
            root / "catalog" / "sports-news",
            root / "catalog" / "sports" / "sideline.json",
        )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        tasks = []
        if poller is not None:
            await asyncio.to_thread(poller.refresh)
            tasks.append(asyncio.create_task(_poll_loop(poller.refresh, cfg.wires.refresh_seconds)))
        if market_poller is not None:
            await asyncio.to_thread(market_poller.refresh)
            tasks.append(asyncio.create_task(_poll_loop(market_poller.refresh, cfg.markets.refresh_seconds)))
        if trade_poller is not None:
            await asyncio.to_thread(trade_poller.refresh)
            tasks.append(asyncio.create_task(_poll_loop(trade_poller.refresh, cfg.trade.refresh_seconds)))
        if weather_poller is not None:
            await asyncio.to_thread(weather_poller.refresh)
            tasks.append(asyncio.create_task(_poll_loop(weather_poller.refresh, cfg.weather.refresh_seconds)))
        if sports_poller is not None:
            await asyncio.to_thread(sports_poller.refresh)
            tasks.append(asyncio.create_task(_poll_loop(sports_poller.refresh, cfg.sports.refresh_seconds)))
        if sideline_poller is not None:
            await asyncio.to_thread(sideline_poller.refresh)
            tasks.append(asyncio.create_task(_poll_loop(sideline_poller.refresh, cfg.sports.refresh_seconds)))
        try:
            yield
        finally:
            for task in tasks:
                task.cancel()
            for task in tasks:
                with contextlib.suppress(asyncio.CancelledError):
                    await task

    app = FastAPI(title="Oriel", version=__version__, lifespan=lifespan)
    app.state.config = cfg
    app.state.poller = poller
    app.state.markets = market_poller
    app.state.trade = trade_poller
    app.state.weather = weather_poller
    app.state.sports = sports_poller
    app.state.sideline = sideline_poller
    brief_store = brief
    if brief_store is None:
        try:
            brief_root = root if root is not None else find_repo_root()
            brief_store = BriefStore.open(brief_root, cfg.home_place)
        except FileNotFoundError:
            brief_store = None
    app.state.brief = brief_store
    app.state.recommendations = None
    if root is not None:
        app.state.recommendations = Recommendations(
            root / "catalog",
            root / "catalog" / "sports",
            overrides_path=root / "server" / "state" / "recommendations.json",
        )

    @app.get("/health", response_model=Health)
    def health() -> Health:
        place = cfg.home_place
        return Health(
            status="ok",
            service="oriel",
            version=__version__,
            bind=cfg.bind,
            home_place=HomePlaceStatus(
                id=place.id,
                name=place.name,
                coordinates_set=place.coordinates_set,
            ),
        )

    @app.get("/bays/brief/selection")
    def brief_selection() -> dict:
        if app.state.brief is None:
            raise HTTPException(status_code=404)
        return app.state.brief.payload()

    @app.post("/bays/brief/selection")
    def brief_select(body: BriefChoice) -> dict:
        if app.state.brief is None:
            raise HTTPException(status_code=404)
        try:
            app.state.brief.choose(body.slot, body.id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return app.state.brief.payload()

    @app.get("/bays/wires")
    def wires_bay() -> dict:
        if app.state.poller is None:
            return {"id": "wires", "panels": []}
        return {"id": "wires", "panels": _stamp(app.state.poller.panels(), cfg.wires.refresh_seconds)}

    @app.get("/bays/markets")
    def markets_bay() -> dict:
        if app.state.markets is None:
            return {"id": "markets", "panels": []}
        return {"id": "markets", "panels": _stamp(app.state.markets.panels(), cfg.markets.refresh_seconds)}

    @app.get("/bays/trade")
    def trade_bay() -> dict:
        if app.state.trade is None:
            return {"id": "trade", "panels": []}
        return {"id": "trade", "panels": _stamp(app.state.trade.panels(), cfg.trade.refresh_seconds)}

    @app.get("/bays/storm")
    def storm_bay() -> dict:
        if app.state.weather is None:
            return {"id": "storm", "panels": []}
        return {"id": "storm", "panels": _stamp(app.state.weather.panels(), cfg.weather.refresh_seconds)}

    @app.get("/bays/field")
    def field_bay() -> dict:
        if app.state.sports is None:
            return {"id": "field", "panels": []}
        return {"id": "field", "panels": _stamp(app.state.sports.panels_for("field"), cfg.sports.refresh_seconds)}

    @app.post("/bays/field/follows")
    def field_follows(body: FollowCommand) -> dict:
        if app.state.sports is None:
            raise HTTPException(status_code=404)
        try:
            app.state.sports.follow(body.competition_id, body.follow)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        app.state.sports.refresh()
        return {"id": "field", "panels": _stamp(app.state.sports.panels_for("field"), cfg.sports.refresh_seconds)}

    @app.get("/bays/far")
    def far_bay() -> dict:
        if app.state.sports is None:
            return {"id": "far", "panels": []}
        return {"id": "far", "panels": _stamp(app.state.sports.panels_for("far"), cfg.sports.refresh_seconds)}

    @app.get("/bays/sideline")
    def sideline_bay() -> dict:
        if app.state.sideline is None:
            return {"id": "sideline", "panels": []}
        return {"id": "sideline", "panels": _stamp(app.state.sideline.panels(), cfg.sports.refresh_seconds)}

    @app.post("/bays/sideline/focus")
    def sideline_focus(body: SportFocus) -> dict:
        if app.state.sideline is None:
            raise HTTPException(status_code=404)
        try:
            app.state.sideline.focus(body.sport, body.follow)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        app.state.sideline.refresh()
        return {"id": "sideline", "panels": _stamp(app.state.sideline.panels(), cfg.sports.refresh_seconds)}

    @app.get("/bays/fantasy")
    def fantasy_bay() -> dict:
        if app.state.sports is None:
            return {"id": "fantasy", "panels": []}
        return {"id": "fantasy", "panels": _stamp(app.state.sports.panels_for("fantasy"), cfg.sports.refresh_seconds)}

    @app.post("/bays/fantasy/select")
    def fantasy_select(body: PlayerCommand) -> dict:
        return _fantasy_command("select", body.player_id)

    @app.post("/bays/fantasy/pin")
    def fantasy_pin(body: PlayerCommand) -> dict:
        return _fantasy_command("pin", body.player_id)

    @app.post("/bays/fantasy/unpin")
    def fantasy_unpin(body: PlayerCommand) -> dict:
        return _fantasy_command("unpin", body.player_id)

    @app.post("/bays/fantasy/flex")
    def fantasy_flex(body: PlayerCommand) -> dict:
        return _fantasy_command("flex", body.player_id)

    @app.post("/bays/fantasy/drop")
    def fantasy_drop(body: PlayerCommand) -> dict:
        return _fantasy_command("drop", body.player_id)

    @app.post("/bays/fantasy/scoring")
    def fantasy_scoring(body: ScoringCommand) -> dict:
        if app.state.sports is None:
            raise HTTPException(status_code=404)
        try:
            app.state.sports.scoring(body.scoring)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"id": "fantasy", "panels": _stamp(app.state.sports.panels_for("fantasy"), cfg.sports.refresh_seconds)}

    def _fantasy_command(action: str, player_id: str) -> dict:
        if app.state.sports is None:
            raise HTTPException(status_code=404)
        method = getattr(app.state.sports, action)
        try:
            method(player_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="player not in the catalog") from exc
        return {"id": "fantasy", "panels": _stamp(app.state.sports.panels_for("fantasy"), cfg.sports.refresh_seconds)}

    @app.get("/suggestions")
    def suggestions() -> dict:
        if app.state.recommendations is None:
            raise HTTPException(status_code=404)
        suggestion = app.state.recommendations.suggestion(_sources(), datetime.now(timezone.utc))
        return {
            "desk_id": suggestion.desk_id,
            "reason": suggestion.reason,
            "panels": list(suggestion.panels),
            "applied": False,
        }

    @app.post("/suggestions/pin")
    def pin_bay(body: BayPin) -> dict:
        return _override("pin", body.bay_id)

    @app.post("/suggestions/dismiss")
    def dismiss_desk(body: DeskDismiss) -> dict:
        return _override("dismiss", body.desk_id)

    @app.post("/suggestions/clear")
    def clear_overrides() -> dict:
        if app.state.recommendations is None:
            raise HTTPException(status_code=404)
        app.state.recommendations.clear()
        return suggestions()

    def _override(action: str, ident: str) -> dict:
        if app.state.recommendations is None:
            raise HTTPException(status_code=404)
        try:
            getattr(app.state.recommendations, action)(ident)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return suggestions()

    def _sources() -> dict:
        return {
            "wires": app.state.poller,
            "markets": app.state.markets,
            "trade": app.state.trade,
            "storm": app.state.weather,
            "weather": app.state.weather,
            "sports": app.state.sports,
            "field": app.state.sports,
            "fantasy": app.state.sports,
            "sideline": app.state.sideline,
        }

    @app.get("/panels/{panel_id}")
    def panel(panel_id: str) -> dict:
        for source in (app.state.poller, app.state.markets, app.state.trade, app.state.weather, app.state.sports, app.state.sideline):
            if source is None:
                continue
            found = source.panel(panel_id)
            if found is not None:
                return _stamp([found], _refresh_for(source))[0]
        raise HTTPException(status_code=404)

    def _refresh_for(source: object) -> int:
        if source is app.state.poller:
            return cfg.wires.refresh_seconds
        if source is app.state.markets:
            return cfg.markets.refresh_seconds
        if source is app.state.trade:
            return cfg.trade.refresh_seconds
        if source is app.state.weather:
            return cfg.weather.refresh_seconds
        return cfg.sports.refresh_seconds

    return app


def _stamp(panels: list[dict], refresh_seconds: int) -> list[dict]:
    stamped = []
    for panel in panels:
        copy = dict(panel)
        copy["refresh_seconds"] = refresh_seconds
        stamped.append(copy)
    return stamped


async def _poll_loop(refresh: Callable[[], None], refresh_seconds: int) -> None:
    while True:
        await asyncio.sleep(max(refresh_seconds, 1))
        await asyncio.to_thread(refresh)


app = create_app()
