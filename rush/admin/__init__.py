# We need to import admin models here so Django picks them up...
from rush.admin import map
from rush.admin.basemap_source.basemap_source import BasemapSourceAdmin
from rush.admin.filters import PublishedStateFilter
from rush.admin.icon import IconAdmin
from rush.admin.initiative import InitiativeAdmin, InitiativeTagAdmin
from rush.admin.page import PageAdmin
from rush.admin.question import QuestionAdmin, QuestionSashAdmin
from rush.admin.region import RegionAdmin
