"""Adapters package."""

from .base import BaseAdapter
from .cricsheet import CricsheetAdapter
from .football import FootballAdapter
from .wikidata import WikidataComicAdapter

__all__ = ["BaseAdapter", "CricsheetAdapter", "FootballAdapter", "WikidataComicAdapter"]
