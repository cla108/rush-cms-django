import {type Style, type MapData, getStyleById, getMapDataById} from "./graphql"
import type { FeatureCollection, Geometry, Feature, Point, Position } from 'geojson';
import type {PathOptions, StyleFunction, CircleMarkerOptions} from "leaflet"
import * as L from 'leaflet';
import { coerceNumbersDeep, blendHexColors, interpolateNumbers, getCentroid } from "./utils/math";
import { waitForElementById, expectEl, ThrottledSignalReceiver, expectQuerySelector } from "./utils/timing";
import { Parser } from 'expr-eval';
import Mustache from "mustache";
import { DynamicSubscriberManager } from './utils/events'
import centerOfMass from "@turf/center-of-mass";
import { circle } from "turf";

/************
 * This script draws a map layer preview based on the currently selected map-data object and
 * the combination of style on layer objects currently being applied to the map layer.
 ************/

interface Tooltip {
    label: string,
    offsetX: number,
    offsetY: number,
    opacity: number,
    direction: string,
    permanent: boolean,
    sticky: boolean,
}

export interface StyleOnLayer{
    
    style: Style,
    feature_mapping: string,
    inlineRow: Element,

    drawPopup: boolean,
    popupTemplate: string | null,

    drawTooltip: boolean,
    tooltip: Tooltip,

}

export interface MapPreviewState {
    isUpdating: boolean,
    stylesOnLayer: Array<StyleOnLayer>,
    currentLayer: L.GeoJSON<any, Geometry> | null,
    centroidMarkers: L.LayerGroup,
    centroidTooltips: L.LayerGroup,
}

/**
 * Represents a change in the map preview state.
 */
export interface MapPreviewUpdate {
    type: "Style" | "MapData",
}
export interface StyleUpdate extends MapPreviewUpdate {
    newStylesOnLayers: Array<StyleOnLayer>,
}
export interface MapDataUpdate extends MapPreviewUpdate {
    newGeoJsonData: FeatureCollection<Geometry, any> | null,
}

interface AppliedStyle{
    styleOnLayer: StyleOnLayer,
    popupTemplate: string | null,
}

interface PopupMetadata {
    __hasPopup: boolean;
    __popupHTML: string | null;
    __popupOptions: object | null;
}

/**
 * Search all style-on-layer inlines and collect their form data + any related data that may exist.
 * Returns a list of style-on-layers to be rendered.
 */
export async function getStyleUpdate(): Promise<StyleUpdate> {
    const stylesOnLayers: Array<StyleOnLayer> = [];
    for (let inlineRow of document.querySelectorAll("[id^='stylesonlayer_set-']:not([id$='-group'])")){
        // for each styleOnLayer inline group
        const styleId = (inlineRow.querySelector("select[id*='-style']") as HTMLSelectElement)?.value;
        const featureMapping = (inlineRow.querySelector("textarea[id*='feature_mapping']") as HTMLInputElement | null)?.value;
        const popupTemplate = (inlineRow.querySelector("textarea[id*='popup']") as HTMLInputElement | null)?.value;
        const drawPopupChecked = (inlineRow.querySelector("input[id*='-draw_popup']") as HTMLInputElement | null)?.checked;
        const drawTooltipChecked = (inlineRow.querySelector("input[id*='-draw_tooltip']") as HTMLInputElement | null)?.checked;
        const tooltipLabel = (inlineRow.querySelector("textarea[id*='label']") as HTMLInputElement | null)?.value;
        const tooltipOffsetX = (inlineRow.querySelector("input[id*='offset_x']") as HTMLInputElement | null)?.value;
        const tooltipOffsetY = (inlineRow.querySelector("input[id*='offset_y']") as HTMLInputElement | null)?.value;
        const tooltipOpacity = (inlineRow.querySelector("input[id*='opacity']") as HTMLInputElement | null)?.value;
        const tooltipDirection = (inlineRow.querySelector("select[id*='direction']") as HTMLInputElement | null)?.value;
        const tooltipPermanent = (inlineRow.querySelector("input[id*='permanent']") as HTMLInputElement | null)?.checked;
        const tooltipSticky = (inlineRow.querySelector("input[id*='sticky']") as HTMLInputElement | null)?.checked;
        if (!(styleId && featureMapping)){
            // most likely an empty inline
            continue;
        }
        const style = await getStyleById(styleId);
        if (
            style !== null && 
            featureMapping !== undefined && 
            popupTemplate !== undefined && 
            drawPopupChecked !== undefined && 
            drawTooltipChecked !== undefined &&
            tooltipLabel !== undefined &&
            tooltipOffsetX !== undefined &&
            tooltipOffsetY !== undefined &&
            tooltipOpacity !== undefined &&
            tooltipDirection !== undefined &&
            tooltipPermanent !== undefined &&
            tooltipSticky !== undefined
        ){
            const tooltipData = {
                label: tooltipLabel,
                offsetX: Number.parseFloat(tooltipOffsetX),
                offsetY: Number.parseFloat(tooltipOffsetY),
                opacity: Number.parseFloat(tooltipOpacity),
                direction: tooltipDirection,
                permanent: tooltipPermanent,
                sticky: tooltipSticky,
            };
            const styleOnLayerData = {
                style: style,
                feature_mapping: featureMapping,
                inlineRow: inlineRow,
                drawPopup: drawPopupChecked,
                popupTemplate: popupTemplate,
                drawTooltip: drawTooltipChecked,
                tooltip: tooltipData,
            };
            stylesOnLayers.push(styleOnLayerData);
        } else {
            const tooltipData = {
                label: tooltipLabel,
                offsetX: tooltipOffsetX !== undefined ? Number.parseFloat(tooltipOffsetX) : Number.NaN,
                offsetY: tooltipOffsetY !== undefined ? Number.parseFloat(tooltipOffsetY) : Number.NaN,
                opacity: tooltipOpacity !== undefined ? Number.parseFloat(tooltipOpacity) : Number.NaN,
                direction: tooltipDirection,
                permanent: tooltipPermanent,
                sticky: tooltipSticky,
            };
            const styleOnLayerData = {
                style: style,
                feature_mapping: featureMapping,
                inlineRow: inlineRow,
                drawPopup: drawPopupChecked,
                popupTemplate: popupTemplate,
                drawTooltip: drawTooltipChecked,
                tooltip: tooltipData,
            };
            console.warn("One or more expected values in a StyleOnLayer inline is missing: ", styleOnLayerData);
        }
    }
    return {
        type: "Style",
        newStylesOnLayers: stylesOnLayers,
    };
}

async function mapDataFromSpan(mapDataSelectSpan: HTMLSpanElement): Promise<MapData | null> {
    let mapDataId = null;
    for (let child of mapDataSelectSpan.childNodes){
        if (child instanceof HTMLOptionElement && child.selected){
            mapDataId = child.value;
        }
    }
    if (mapDataId === null || mapDataId === ""){
        return null;
    }
    return await getMapDataById(mapDataId);
}

/**
 * Fetch GeoJSON using the UUID present in the map-data input field.
 */
export async function getMapDataUpdate(mapDataSelectSpan: HTMLSpanElement): Promise<MapDataUpdate>{
    const clearMapData = {type: "MapData", newGeoJsonData: null} as MapDataUpdate;
    const mapData = await mapDataFromSpan(mapDataSelectSpan);
    if (mapData === null){
        return clearMapData;
    } else if (mapData.geojson === null){
        return clearMapData;
    }
    const geojson = JSON.parse(mapData.geojson);
    if (geojson.features === null || geojson.features === undefined){
        return clearMapData;
    }
    return {
        type: "MapData",
        newGeoJsonData: geojson as FeatureCollection,
    }
}


/**
 * Namespaced accessor for adding StyleOnLayer inline element event listeners. 
 * This code isn't the most efficient, but I'm leaving it for now because it works...
 */
export const inlineElements = {
    styles: {
        addEventListener: (callback: (mutation: MutationRecord) => void): void => {
            const inlineGroup = document.getElementById('stylesonlayer_set-group');
            if (inlineGroup !== null) {
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.target instanceof HTMLSelectElement && mutation.type === "childList"){
                            callback(mutation);
                        }
                    });
                });
                observer.observe(inlineGroup, {childList: true, subtree: true});
            }
        },
    },
    featureMappings: {
        addEventListener: (callback: (event: Event) => void): void => {
            document.addEventListener('input', (event) => {
                const target = event.target;
                const featureChanged = target instanceof HTMLTextAreaElement && target.id.includes('feature_mapping');
                if (featureChanged) {
                    callback(event);
                }
            });
        },
    },
    popups: {
         addEventListener: (callback: (mutation: MutationRecord) => void): void => {
            const inlineGroup = document.getElementById('stylesonlayer_set-group');
            if (inlineGroup !== null) {
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach((mutation) => {
                        if (mutation.target instanceof HTMLSelectElement && mutation.type === "childList"){
                            callback(mutation);
                        }
                    });
                });
                observer.observe(inlineGroup, {childList: true, subtree: true});
            }
        },
    },
};

/**
 * Find which styles apply to a given GeoJSON feature.
 * @param feature the feature to get applied styles for.
 * @param stylesOnLayer the styles present on the current map layer.
 * @returns an array of styles that should be applied to the given feature. 
 */
function getAppliedStyles(feature: Feature<Geometry, any>, stylesOnLayer: Array<StyleOnLayer>): Array<AppliedStyle>{
    const parser = new Parser();
    let applied: Array<AppliedStyle> = [];
    for (let styleOnLayer of stylesOnLayer){
        const fieldMappingContainer = styleOnLayer.inlineRow.querySelector("td[class*='feature_mapping']");
        const fieldMappingErrors = fieldMappingContainer?.querySelector("div[id*='errors']");
        try{
            const expr = parser.parse(styleOnLayer.feature_mapping);
            if (expr.evaluate(coerceNumbersDeep(feature.properties)) === true){
                applied.push({styleOnLayer: styleOnLayer, popupTemplate: styleOnLayer.popupTemplate});
                if (fieldMappingErrors && fieldMappingContainer){
                    fieldMappingContainer.removeChild(fieldMappingErrors);
                }
            }
        } catch (error){
            // TODO: If a variable isn't in ANY of the features then we can display it here, otherwise if it's 
            // being used at least once I don't think I should display an error since the style is technically 
            // being applied.

            // TODO: Error propagating code is NOT efficient! I should probably make this faster...

            // Add an error message above the feature mapping textarea for the user if parsing fails.
            if (fieldMappingErrors && fieldMappingContainer){
                fieldMappingContainer.removeChild(fieldMappingErrors);
            }
            if (fieldMappingContainer && !fieldMappingContainer?.querySelector("div[id*='errors']")){
                const errorEl = document.createElement("div");
                errorEl.textContent = String(error);
                errorEl.id = "errors";
                errorEl.style = "color:rgb(255, 0, 0);";
                fieldMappingContainer.insertBefore(errorEl, fieldMappingContainer.children[0]);
            }   
        }
    }
    return applied;
}

function getDefaultPolygonStyle(): PathOptions{
    return {
        // Path fill options.
        fill: true,
        fillColor: "#4B3EFF",
        fillOpacity: 0.3,
        // Path stroke options.
        stroke: true,
        weight: 1,
        opacity: 1,
        color: "#4B3EFF",
        dashArray: "1 10",
        dashOffset: "0",
        lineCap: "round",
        lineJoin: "round",
    };
}

/**
 * Get a function used to style polygon GeoJSON features on a leaflet map.
 * @param state the MapPreviewState.
 * @returns a leaflet StyleFunction.
 */
function getPolygonStyleFunc(state: MapPreviewState): StyleFunction {
    const func = (feature: Feature<Geometry, any>) => {

        // point styles are handled by getPointStyleFunc (we don't want to override them here!)
        if (feature.geometry.type === 'Point' || feature.geometry.type === 'MultiPoint') {
            return {};
        }

        // If no stylesOnLayers are in the map preview state, just return a default polygon styling.
        if (state.stylesOnLayer.length == 0 && !state.isUpdating){
            return getDefaultPolygonStyle();
        }

        // Otherwise, build path options from the styles. If there are multiple
        // styles being applied to the same feature, we just give our
        // best guess at how the user wants their map to look by interpolating them
        // or overriding if they can't be interpolated.
        let appliedStyles = getAppliedStyles(feature, state.stylesOnLayer);
        
        let drawFill = false;
        let fillOpacity = undefined;
        let fillColor = undefined;
        
        let drawStroke = false;
        let strokeOpacity = undefined;
        let strokeColor = undefined;
        let strokeWeight = undefined;

        // Style attributes that can't be interpolated (just take the most recent one from the applied styles)
        let strokeDashArray = "";
        let strokeDashOffset = undefined; // technically can be interpolated but I don't think it would be intuitive for a user
        let strokeLineCap = "round";
        let strokeLineJoin = "round";

        for (let appliedStyle of appliedStyles){
            const style = appliedStyle.styleOnLayer.style;

            // If one style draws something then the combined style will also draw that thing
            if (style.drawFill === true){
                drawFill = true;
            }
            if (style.drawStroke === true){
                drawStroke = true;
            }

            fillOpacity = interpolateNumbers(fillOpacity, style.fillOpacity);
            strokeOpacity = interpolateNumbers(strokeOpacity, style.strokeOpacity);
            strokeWeight = interpolateNumbers(strokeWeight, style.strokeWeight);

            if (fillColor === undefined){
                fillColor = style.fillColor;
            } else {
                // interpolate fill color
                fillColor = blendHexColors(fillColor, style.fillColor, 0.5);
            }
            if (strokeColor === undefined){
                strokeColor = style.strokeColor;
            } else {
                // interpolate stroke color
                strokeColor = blendHexColors(strokeColor, style.strokeColor, 0.5);
            }

            // Just override the rest without interpolation...
            if (style.strokeDashArray !== null){
                strokeDashArray = style.strokeDashArray;
            }
            if (style.strokeDashOffset !== null){
                strokeDashOffset = style.strokeDashOffset;
            }
            strokeLineJoin = style.strokeLineJoin;
            strokeLineCap = style.strokeLineCap;
        }
        const polygonStyleProps = {
            // Path fill options.
            fill: drawFill,
            fillColor: fillColor,
            fillOpacity: fillOpacity,
            // Path stroke options
            stroke: drawStroke,
            weight: strokeWeight,
            opacity: strokeOpacity,
            color: strokeColor,
            dashArray: strokeDashArray,
            dashOffset: strokeDashOffset,
            lineCap: strokeLineCap as L.LineCapShape,
            lineJoin: strokeLineJoin as L.LineJoinShape,
        }

        // Inject style props into properties for layer serialization
        feature.properties.__style = polygonStyleProps;

        return polygonStyleProps;
    };
    return func as StyleFunction;
}

/**
 * Get styled properties for a marker div icon.
 * @param baseMediaUrl the base media url for the RUSH admin server.
 * @param markerStyle the marker style.
 */
function getMarkerDivIconProps(baseMediaUrl: string, markerStyle: Style): any{
    const markerImageWidth = markerStyle.markerSize;
    const markerRadius = Math.sqrt(Math.pow(markerImageWidth / 2, 2) + Math.pow(markerImageWidth / 2, 2));
    return {
        html: `
            <div>
                <div style="
                    width: ${markerRadius * 2}px;
                    height: ${markerRadius * 2}px;
                    background-color: ${markerStyle.markerBackgroundColor};
                    opacity: ${markerStyle.markerBackgroundOpacity};
                    border-radius: 50%;
                    display: flex;
                    position: absolute;
                "></div>
                <img 
                    src="${baseMediaUrl + markerStyle.markerIcon}"
                    style="
                        width: ${markerImageWidth}px; 
                        height: ${markerImageWidth}px;
                        opacity: ${markerStyle.markerIconOpacity};
                        position: relative;
                        top: ${markerRadius - (markerImageWidth / 2)}px;
                        left: ${markerRadius - (markerImageWidth / 2)}px;
                    "
                />
            </div>
        `,
        className: '', // Disable default Leaflet styles
        iconSize: [markerRadius * 2, markerRadius * 2],
        iconAnchor: [markerRadius, markerRadius], // Center the icon around the latlng
    };
}

/**
 * Get a function used to style Point GeoJSON features on a leaflet map.
 * @param baseMediaUrl the base URL for fetching media files from the server.
 * @param state the current map preview state.
 * @returns a function that returns a leaflet marker object.
 */
function getPointStyleFunc(baseMediaUrl: string, state: MapPreviewState): (feature: Feature<Point, any>, latlng: L.LatLng) => L.Marker | L.Circle | undefined{
    // canvas is initialized once per render-cycle, since this executes at function-build time.
    const circleCanvas = L.canvas()
    const func = (feature: Feature<Point, any>, latlng: L.LatLng) => {

        // Grab the first applied style that has a non-empty marker icon configured to be drawn
        // TODO:    When moving this style-resolution code down into the backend, remember to draw a marker
        //          background color if there is no icon style but a background color is specified and 
        //          draw-marker is true.
        let markerStyle: Style | null = null;
        let circleStyle: Style | null = null;  // grab the first applied circle style as well
        const appliedStyles = getAppliedStyles(feature, state.stylesOnLayer);
        for (let appliedStyle of appliedStyles){
            const style = appliedStyle.styleOnLayer.style;
            if (style.drawMarker === true){
                markerStyle = style;
            }
            else if (style.drawCircle === true){
                circleStyle = style;
            }
        }

        if (markerStyle === null && circleStyle === null){
            // Don't return a leaflet marker object if the style doesn't necessitate drawing anything to the screen
            return undefined;
        }
        else if (circleStyle !== null){
            // inject circle props for serialization and return a circle
            const circleOptions = {
                radius: circleStyle.circleRadius,
                fill: true,
                fillColor: circleStyle.circleFillColor,
                fillOpacity: circleStyle.circleFillOpacity,
                stroke: true,
                color: circleStyle.circleStrokeColor,
                weight: circleStyle.circleStrokeWeight,
                opacity: circleStyle.circleStrokeOpacity,
                lineCap: circleStyle.circleStrokeLineCap,
                lineJoin: circleStyle.circleStrokeLineJoin,
                dashArray: circleStyle.circleStrokeDashArray,
                dashOffset: circleStyle.circleStrokeDashOffset,
            } as CircleMarkerOptions;
            feature.properties.__circleOptions = circleOptions;
            return L.circle(latlng, {...circleOptions, renderer: circleCanvas});
        }
        else if (markerStyle !== null){
            // inject marker div icon props for serialization and return a marker div icon
            const markerDivIconProps = getMarkerDivIconProps(baseMediaUrl, markerStyle);
            feature.properties.__pointDivIconStyleProps = markerDivIconProps;
            return L.marker(latlng, {icon: new L.DivIcon(markerDivIconProps)});
        }
    };
    return func;
}

/**
 * Get a centroid Point from a group 
 * @param polygonCoords 
 * @returns 
 */
function getPolygonCentroid(polygonCoords: Position[]): L.Point{
    const points: Array<L.Point> = [];
    for (let coord of polygonCoords){
        points.push(new L.Point(coord[0], coord[1]))
    }
    return getCentroid(points);
}

async function showSpinner(){

    // Don't let users submit the form while the map-preview is loading.
    const saveBtn = expectQuerySelector(document.body, "input[name='_save']") as HTMLInputElement;
    const addAnotherBtn = expectQuerySelector(document.body, "input[name='_addanother']") as HTMLInputElement;
    const continueBtn = expectQuerySelector(document.body, "input[name='_continue']") as HTMLInputElement;
    saveBtn.disabled = true;
    addAnotherBtn.disabled = true;
    continueBtn.disabled = true;

    const mapPreviewEl = document.getElementById("map-preview");
    const spinnerEl = document.getElementById("map-spinner");
    if (mapPreviewEl !== null && spinnerEl !== null){
        mapPreviewEl.classList.add('blur');
        spinnerEl.classList.remove('hidden');
    } else {
        console.error("Couldn't find map-preview and map-spinner in the DOM!");
    }

}

function hideSpinner(){
    
    const saveBtn = expectQuerySelector(document.body, "input[name='_save']") as HTMLInputElement;
    const addAnotherBtn = expectQuerySelector(document.body, "input[name='_addanother']") as HTMLInputElement;
    const continueBtn = expectQuerySelector(document.body, "input[name='_continue']") as HTMLInputElement;
    saveBtn.disabled = false;
    addAnotherBtn.disabled = false;
    continueBtn.disabled = false;
    
    const mapPreviewEl = document.getElementById("map-preview");
    const spinnerEl = document.getElementById("map-spinner");
    if (mapPreviewEl !== null && spinnerEl !== null){
        mapPreviewEl.classList.remove('blur');
        spinnerEl.classList.add('hidden');
    } else {
        console.error("Couldn't find map-preview and map-spinner in the DOM!");
    }
}

function showSpinnerAfter(numSeconds: number, state: MapPreviewState): void {
    setTimeout(() => {
        if (state.isUpdating){
            showSpinner();
        }
    }, numSeconds * 1000)
}

/**
 * Extract latitude / longitude positions from a set of geometry coordinates. This function is used to normalize
 * the feature geometry across Polygons and MultiPolygons because I have found that the array nesting is not consistent 
 * depending on the GeoJSON data being pushed into the system at runtime...
 * @param coordinates any leaflet "feature.geometry.coordinates" object.
 * @returns an array of "polygons", which are defined here as a list of lists of numbers, where the innermost list only ever 
 * has 2 elements (lat and long).
 */
function extractLatLngGroups(coordinates: any): Position[][] {
    const result: Position[][] = [];
    function traverse(node: any): void {
        if (Array.isArray(node) && node.length > 0) {
            if (typeof node[0] === 'number' && typeof node[1] === 'number') {
                // Base case: This is a Position, add as a group
                result.push([node as Position]);
            } else if (typeof node[0][0] === 'number') {
                // This is a flat array of Positions
                result.push(node as Position[]);
            } else {
                // Still nested, keep traversing
                for (const child of node) {
                    traverse(child);
                }
            }
        }
    }
    traverse(coordinates);
    return result;
}

/**
 * Get the popup metadata from the given popup template.
 * @param popupTemplate a string, or null, if no template exists.
 * @returns some popup metadata that can be used to tell leaflet how, and whether,
 * to render a popup.
 */
function getPopupMetadata(feature: Feature<Geometry, any>, popupTemplate: string | null): PopupMetadata {
    if (popupTemplate === null){
        return {
            __hasPopup: false,
            __popupHTML: null,
            __popupOptions: null,
        };
    }

    // Hack for resizing popup images to always fit inside the popup container. There is probably a better way to do this.
    let hasImage = false;
    popupTemplate = popupTemplate.replace(/<img(.*?)>/g, (match) => {
        hasImage = true;
        return match.replace('<img', '<img style="max-width:250px; height:auto;"');
    });
    const renderedPopup = Mustache.render(popupTemplate, feature.properties);
    const popupOptions = {
        maxWidth: 250,
        // Shrink the popup container to the size of the text if no image is present in the popup.
        // Otherwise, resize the image width to be 250 pixels and set the minimum popup container 
        // to be the same size as well.
        minWidth: hasImage ? 250 : 0,
    };

    return {
        __hasPopup: true,
        __popupHTML: renderedPopup,
        __popupOptions: popupOptions,
    };
}

/**
 * Flatten a list of "applied styles" to a popup template, or null.
 * @param appliedStyles a list of styles applied to some feature.
 * @returns a string template, or null if no popup template is defined (and enabled) in any of the applied styles.
 */
function getPopupTemplate(appliedStyles: Array<AppliedStyle>): string | null {
    let popupTemplate = null;
    for (let appliedStyle of appliedStyles){
        if (appliedStyle.popupTemplate !== null && appliedStyle.popupTemplate !== "" && appliedStyle.styleOnLayer.drawPopup === true){
            popupTemplate = appliedStyle.popupTemplate;
        }
    }
    return popupTemplate;
}

function drawMapPreview(map: L.Map, state: MapPreviewState, update: MapPreviewUpdate): void {

    // Always remove the previous layer, if there is one, from the map. 
    // Otherwse, it overlaps with the new layer being drawn.
    if (state.currentLayer !== null){
        map.removeLayer(state.currentLayer);
    }
    state.centroidMarkers.clearLayers();
    state.centroidTooltips.clearLayers();

    // Update currentLayer if we are receiving new map data.
    if ("MapData" === update.type){
        const newGeoJson = (update as MapDataUpdate).newGeoJsonData;
        if (newGeoJson === null){
            state.currentLayer = null;
        } else {
            state.currentLayer = L.geoJSON(newGeoJson);
            map.fitBounds(state.currentLayer.getBounds());
        }
    }

    // Update stylesOnLayer if we are receiving new style data
    else if ("Style" === update.type) {
        state.stylesOnLayer = (update as StyleUpdate).newStylesOnLayers;
    }

    /**
     * Begin drawing the map.
     */

    if (state.currentLayer === null){
        // Exit if there is no layer to draw at this point...
        return;
    }
    
    const baseMediaUrl = expectEl('injected-media-url').innerHTML;
    const anyMarkerStyles = state.stylesOnLayer.filter(styleOnLayer => styleOnLayer.style.drawMarker == true).length > 0;
    const styledGeoJsonData = L.geoJSON(state.currentLayer.toGeoJSON(), {
        renderer: L.canvas(),
        style: getPolygonStyleFunc(state),
        pointToLayer: getPointStyleFunc(baseMediaUrl, state),
        onEachFeature: (feature, layer) => {

            const appliedStyles = getAppliedStyles(feature, state.stylesOnLayer);
            const popupTemplate = getPopupTemplate(appliedStyles);
            const popupMetadata = getPopupMetadata(feature, popupTemplate);
            if (popupMetadata.__hasPopup === true && popupMetadata.__popupHTML !== null && popupMetadata.__popupOptions !== null){
                layer.bindPopup(popupMetadata.__popupHTML, popupMetadata.__popupOptions);
                feature.properties = {...feature.properties, ...popupMetadata};
            }

            const [featureCenterLng, featureCenterLat] = centerOfMass(feature).geometry.coordinates;

            // Flatten the list of applied styles to a single tooltip and apply it, if one is enabled.
            let tooltip: Tooltip | null = null;
            for (let appliedStyle of appliedStyles){
                if (appliedStyle.styleOnLayer.drawTooltip === true){
                    tooltip = appliedStyle.styleOnLayer.tooltip;
                    break;
                }
            }
            if (tooltip !== null){
                const renderedTooltipLabel = Mustache.render(tooltip.label, feature.properties);
                const tooltipOptions = {
                    offset: new L.Point(tooltip.offsetX, tooltip.offsetY),
                    opacity: tooltip.opacity,
                    direction: tooltip.direction as L.Direction,
                    permanent: tooltip.permanent,
                    sticky: tooltip.sticky,
                    className: 'leaflet-label'
                };
                const leafletTooltip = L.tooltip(tooltipOptions);
                leafletTooltip.setLatLng([featureCenterLat, featureCenterLng]);
                leafletTooltip.setContent(renderedTooltipLabel);
                leafletTooltip.addTo(state.centroidTooltips);
                feature.properties = {...feature.properties, "__hasTooltip": true, "__tooltipLat": featureCenterLat, "__tooltipLng": featureCenterLng, "__tooltipHTML": renderedTooltipLabel, "__tooltipOptions": tooltipOptions};
            } else {
                feature.properties = {...feature.properties, "__hasTooltip": false};
            }

            // Draw centroid icon markers when a marker icon style is applied to a polygon feature
            const isPolygon = feature.geometry.type === "MultiPolygon" || feature.geometry.type == "Polygon";
            if (isPolygon && anyMarkerStyles){
                const markerStyles = appliedStyles.filter(appliedStyle => appliedStyle.styleOnLayer.style.drawMarker == true);
                if (markerStyles.length > 0){
                    const markerStyle = markerStyles[0].styleOnLayer.style; // Just take the first marker style if multiple applied.
                    const bindCentroidMarkerIcon = (lat: Number, lng: Number) => {
                        const markerDivIconProps = getMarkerDivIconProps(baseMediaUrl, markerStyle);
                        // Build the centroid marker icon feature with serializable divIcon and popup metadata
                        const centroidMarkerIconFeature = {
                            type: "Feature",
                            geometry: { type: "Point", coordinates: [lng, lat] },
                            properties: {
                                // Serialize leaflet markerDivIcon properties
                                __pointDivIconStyleProps: markerDivIconProps,

                                // Serialize leaflet popup metadata so it can be re-created later
                                ...popupMetadata,
                            },
                        } as Feature<Point, any>;

                        // Extract a leaflet marker from the feature.
                        const marker = L.geoJSON(centroidMarkerIconFeature, {
                            pointToLayer: (geoJsonPoint, latlng) => L.marker(latlng, {
                                icon: new L.DivIcon(markerDivIconProps),
                            }),
                        }).getLayers()[0];

                        // Bind a leaflet popup to the marker if necessary
                        if (popupMetadata.__hasPopup === true && popupMetadata.__popupHTML !== null && popupMetadata.__popupOptions !== null){
                            marker.bindPopup(popupMetadata.__popupHTML, popupMetadata.__popupOptions);
                        }
                        marker.addTo(state.centroidMarkers);
                    };
                    bindCentroidMarkerIcon(featureCenterLat, featureCenterLng);
                }
            }
        },
    });
    state.currentLayer = styledGeoJsonData;
    styledGeoJsonData.addTo(map)
    hideSpinner();
    state.isUpdating = false;

    // Save serialized leaflet json to a hidden field so it can be saved on the Layer model
    const hiddenField = expectEl("id_serialized_leaflet_json") as HTMLInputElement;
    hiddenField.value = serializeLayer(state);

}

/**
 * Serialize the layer preview information as a Leaflet LayerGroup object.
 * @param state the current map preview state.
 * @returns a string of serialized JSON data with a LayerGroup containing the styled
 * data in the layer preview. 
 */
function serializeLayer(state: MapPreviewState): string {
    let allLayers = new L.LayerGroup(state.centroidMarkers.getLayers());
    state.currentLayer?.addTo(allLayers);
    return JSON.stringify({
        featureCollection: allLayers.toGeoJSON(),
    });
}

/**
 * Add hooks for current and future styles-on-layer inlnes that show/hide element groups when specific checkboxes are selected.
 */
const initStylesOnLayerResponsiveUI = (subscriberManager: DynamicSubscriberManager) => {

    const getFormRowsWithLabelText = (stylesOnLayerInline: HTMLElement, labelText: string): Array<HTMLElement> => {
        // All child form-rows of the inline that themselves have child labels whose text includes labelText.
        const allFormRows = Array.from(stylesOnLayerInline.querySelectorAll('div[class*="form-row"]'));
        const formRowsWithLabel = allFormRows.filter(div => div.querySelector('label')?.textContent.includes(labelText));
        return formRowsWithLabel as Array<HTMLElement>;
    };

    const registerCheckbox = (
        checkboxSelector: string, 
        affectedLabelsSubstring: string, 
        callback: (checkboxFormRow: HTMLElement | null, formRows: Array<HTMLElement>, isChecked: boolean) => void,
    ) => {
        subscriberManager.subscribeEventListener("input", checkboxSelector, (event) => {
            if (event.target !== null && event.target instanceof HTMLInputElement){
                // Grab parent inline when checkbox clicked
                const inline = event.target.closest("div[id*='stylesonlayer_set-']");
                if (inline === null || !(inline instanceof HTMLElement)){
                    throw new Error("Could not find 'draw_tooltip' form-field parent row!");
                }
                // Run callback on matching labelled form-rows
                const labelledFormRows = getFormRowsWithLabelText(inline, affectedLabelsSubstring)
                callback(event.target.closest("div[class*='form-row']"), labelledFormRows, event.target.checked);
            }
        });
        // Simulate an initial event to show/hide based on initial checkbox value on page-load (does not change checkbox value).
        document.querySelectorAll<HTMLInputElement>(checkboxSelector).forEach(
            checkbox => checkbox.dispatchEvent(new Event('input', { bubbles: true }))
        );
    };

    const COLLAPSE_BG_COLOR = "#FFFFFF";
    const EXPAND_BG_COLOR_CHECKBOX = "#E2DBC4";
    const EXPAND_BG_COLOR = "#f6f6f6";

    // Register the draw-tooltip checkbox
    registerCheckbox("input[id*='-draw_tooltip']", "Tooltip", (checkboxFormRow, formRows, checked) => {
        for (let formRow of formRows){
            if (checked === true){
                formRow.style.display = "block";
                formRow.style.setProperty("background-color", EXPAND_BG_COLOR);
                checkboxFormRow?.style.setProperty("background-color", EXPAND_BG_COLOR_CHECKBOX);
            }
            else {
                formRow.style.display = "none";
                formRow.style.setProperty("background-color", COLLAPSE_BG_COLOR);
                checkboxFormRow?.style.setProperty("background-color", COLLAPSE_BG_COLOR);
            }
        }
    });

    // Register the draw-tooltip checkbox
    registerCheckbox("input[id*='-draw_popup']", "Popup", (checkboxFormRow, formRows, checked) => {
        for (let formRow of formRows){
            if (checked === true){
                formRow.style.display = "block";
                formRow.style.setProperty("background-color", EXPAND_BG_COLOR);
                checkboxFormRow?.style.setProperty("background-color", EXPAND_BG_COLOR_CHECKBOX);
            }
            else {
                formRow.style.display = "none";
                formRow.style.setProperty("background-color", COLLAPSE_BG_COLOR);
                checkboxFormRow?.style.setProperty("background-color", COLLAPSE_BG_COLOR);
            }
        }
    });

};

/**
 * Initialize various inputs that trigger "style updates" for the layer preview.
 * There are four basic categories that should generally trigger a re-drawing of
 * the map based on changing styles:
 *  1.  Inline textareas and number input sliders -- These need to be throttled to avoid 
 *      updating too frequently as people type or "slide".
 *  2.  Inline summernote fields -- These need to be polled in order for us to get an event
 *      callback at all. This is because the summernote rich text field lives inside an <iframe>
 *      where DOM events don't "bubble-up".
 *  3.  Inline checkboxes and dropdowns -- These are the simplest and only require a callback (although
 *      it still has to be subscribed to in case new inlines are added when editing).
 *  4.  Non-inline events -- For example, when re-focusing the webpage. It is possible the user is returning
 *      from another django form page, e.g., style, where the changes need to be reflected in the layer preview.
 */
const initStyleUpdateTriggers = (subscriberManager: DynamicSubscriberManager, map: L.Map, mapDataSelectSpan: HTMLSpanElement, mapPreviewState: MapPreviewState) => {
    
    // Shorthand for redrawing the map by fetching new styles / popup info
    const doStyleUpdate = () => {
        mapDataFromSpan(mapDataSelectSpan).then((mapData) => {
            if (mapData?.providerState === "GEOJSON"){
                mapPreviewState.isUpdating = true;
                showSpinnerAfter(1, mapPreviewState);
                getStyleUpdate().then(styleUpdate => {
                    drawMapPreview(map, mapPreviewState, styleUpdate);
                });
            }
        });
    };
    
    // We want to throttle the updates for continous input types (like sliders)
    const throttledStyleUpdate = new ThrottledSignalReceiver(1000, doStyleUpdate);

    // 1. Textareas and input sliders
    subscriberManager.subscribeEventListener("input", "textarea[id*='-feature_mapping']", (e) => throttledStyleUpdate.trigger());
    subscriberManager.subscribeEventListener("input", "input[id*='-offset_x']", (e) => throttledStyleUpdate.trigger());
    subscriberManager.subscribeEventListener("input", "input[id*='-offset_y']", (e) => throttledStyleUpdate.trigger());
    subscriberManager.subscribeEventListener("input", "input[id*='-opacity']", (e) => throttledStyleUpdate.trigger());

    // 2. Summernote editors
    // 
    // NOTE: This only works when the user clicks outside the editor, after entering text. I've spent too many
    // hours trying to get it to update automatically by trying to use the real summernote js library with jquery, and also by
    // trying hacky methods like simulating the click, none of which worked. This is shit, but good enough for now...
    // 
    // Hours wasted: 6
    //               ^^--- Update me if you work on this.
    let previousEditorText = "";
    let currentEditorText = "";
    const summernoteTextAreaSelectors = ["textarea[id*='popup']", "textarea[id*='label']"];
    const pollSummernoteEditorChanges = () => {
        currentEditorText = "";
        for (let selector of summernoteTextAreaSelectors){
            for (let el of document.querySelectorAll(selector)){
                if (el instanceof HTMLTextAreaElement){
                    currentEditorText += el.value;
                }
            }
        }
        if (currentEditorText !== previousEditorText){
            doStyleUpdate();
            previousEditorText = currentEditorText;
        }
        setTimeout(pollSummernoteEditorChanges, 1000);
    };
    pollSummernoteEditorChanges();

    // 3. Checkboxes and dropdowns
    subscriberManager.subscribeMutationObserver({childList: true, subtree: true}, "span[id*='select2-id_stylesonlayer_set']", doStyleUpdate); // Select-2 (autocomplete) dropdown needs DOM observer
    subscriberManager.subscribeEventListener("input", "input[id*='-draw_popup']", doStyleUpdate);
    subscriberManager.subscribeEventListener("input", "input[id*='-draw_tooltip']", doStyleUpdate);
    subscriberManager.subscribeEventListener("change", "select[id*='-direction']", doStyleUpdate);
    subscriberManager.subscribeEventListener("input", "input[id*='-permanent']", doStyleUpdate);
    subscriberManager.subscribeEventListener("input", "input[id*='-sticky']", doStyleUpdate);

    // 4. Non-inline events
    document.addEventListener('visibilitychange', async function () {
        if (document.visibilityState === 'visible') {
            // Listen to redraw the map when the tab is refocused (the user leaves and then comes back).
            // This can happen after a user edits one of the inline styles and then clicks on the layer edit tab.
            doStyleUpdate();
        }
    });    
};

document.addEventListener("DOMContentLoaded", () => {(async () => {
    
    const TILE_LAYER_OPTS = {
        minZoom: 0,
        maxZoom: 22,
        updateWhenIdle: true,
        zIndex: 0,
        attribution: '© <a href="https://www.mapbox.com/about/maps/">Mapbox</a> © <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> <strong><a href="https://www.mapbox.com/map-feedback/" target="_blank">Improve this map</a></strong>',
    }
    const MAPBOX_USER = 'rushadmin'
    const MAPBOX_STYLEID = 'clw2m6f9b018001obfxcc747g'
    const MAPBOX_TOKEN = 'pk.eyJ1IjoicnVzaGFkbWluIiwiYSI6ImNsdzJtYmRydzBuNDIyam5yZ2pwMG16cnUifQ.SkSSdHcrPq4u8HSitBvJcg'
    const API_URL = `https://api.mapbox.com/styles/v1/`
    const API_TILE_PATH = `${MAPBOX_USER}/${MAPBOX_STYLEID}/tiles/256/{z}/{x}/{y}@2x`
    const API_PARAMS = `?access_token=${MAPBOX_TOKEN}`

    // Initialize leaflet map
    let map = L.map('map-preview').setView([0, 0], 2);
    L.tileLayer(API_URL + API_TILE_PATH + API_PARAMS, TILE_LAYER_OPTS).addTo(map);

    // Initialize object to track map preview state
    let mapPreviewState: MapPreviewState = {
        isUpdating: true,
        stylesOnLayer: [],
        currentLayer: null,
        centroidMarkers: new L.LayerGroup(),
        centroidTooltips: new L.LayerGroup(),
    };
    mapPreviewState.centroidMarkers.addTo(map);
    mapPreviewState.centroidTooltips.addTo(map);

    // Move spinner from top of page to inside the map preview box and show the spinner initially as the map preview is drawn
    const mapDataSelectSpan = await waitForElementById("id_map_data");
    (await waitForElementById('id_map_data_helptext')).appendChild(await waitForElementById("map-spinner"));
    const initialMapDataProviderState = (await mapDataFromSpan(mapDataSelectSpan))?.providerState;
    hideSpinner(); // Spinner should be turned off by default... (this is needed so non-gejson map data layers don't initialize with a spinner that never goes away.)
    if (initialMapDataProviderState && initialMapDataProviderState === "GEOJSON"){
        // Render the spinner initially if the being edited is for GEOJSON map-data.
        showSpinner();
    }
    
    const subscriberManager = new DynamicSubscriberManager(document.body);
    initStyleUpdateTriggers(subscriberManager, map, mapDataSelectSpan, mapPreviewState);
    initStylesOnLayerResponsiveUI(subscriberManager);

    // Listen to redraw the map when the map-data is changed.
    const mapPreviewEl = await waitForElementById("map-preview");
    //const stylesOnLayersGroupEl = await waitForElementById("stylesonlayer_set-group");
    async function onMapDataDropdownChange(){
        const mapData = await mapDataFromSpan(mapDataSelectSpan);
        const hideMapPreview = () => {
            mapPreviewEl.style.display = 'none';
        };
        const showMapPreview = () => {
            mapPreviewEl.style.display = 'block';
        };
        if (mapData?.providerState === "GEOJSON"){
            showMapPreview();
            mapPreviewState.isUpdating = true;
            showSpinnerAfter(1, mapPreviewState);
            getMapDataUpdate(mapDataSelectSpan).then((mapDataUpdate) => drawMapPreview(map, mapPreviewState, mapDataUpdate));
        } else {
            // Hide map preview and styles on layers when we are not dealing with GEOJSON map data for this layer...
            hideMapPreview();
        }
    };
    onMapDataDropdownChange(); // for initial load
    mapDataSelectSpan.addEventListener("change", onMapDataDropdownChange); // When new map data is selected

    // Draw the initial map using the current map-data and style info.
    Promise.all([
        getStyleUpdate(), 
        getMapDataUpdate(mapDataSelectSpan),
    ]).then(([styleUpdate, mapDataUpdate]: [StyleUpdate, MapDataUpdate]) => {
        // Inefficient, but meh.
        drawMapPreview(map, mapPreviewState, mapDataUpdate);
        mapPreviewState.isUpdating = true; // Still doing the initial update...
        drawMapPreview(map, mapPreviewState, styleUpdate);
    });

})();});
