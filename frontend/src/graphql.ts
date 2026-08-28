/**
 * Typescript Schema for GraphQL models.
 * 
 * Since the universe of (Admin Site --> GraphQL Backend) API calls should remain
 * relatively small for the foreseeable future, I simply use TypeScript interfaces
 * to spec API calls and the datatypes they return.
 */

/**
 * An error occurred during the GraphQL request.
 */
export class GraphQLRequestFailed extends Error {
    constructor(message: string){
      super(message);
    }
}

/**
 * Make an arbitrary query to GraphQL.
 * @param queryString the query-string to execute.
 * @returns A promise of Any data type. It is the responsibility of the
 * caller to make sure the typed response is correct.
 */
async function executeQuery(queryString: string): Promise<any> {
    const response = await fetch("/graphql/", {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Accept": "application/json",
            // TODO Add CSRF token here
        },
        body: queryString,
    });
    const responseJson = await response.json();
    if (200 !== response.status){
        if (responseJson.errors === null || responseJson.errors === undefined){
            throw new GraphQLRequestFailed("GraphQL response code (" + response.status + ") is not 200 but no errors were sent back in the response!");
        }
        // something went wrong during the request
        throw new GraphQLRequestFailed(JSON.stringify(responseJson.errors));
    }
    // return full response json
    return responseJson;
}

export interface Style{
    // stroke options
    drawStroke: boolean,
    strokeColor: string,
    strokeWeight: number,
    strokeOpacity: number,
    strokeLineJoin: string,
    strokeLineCap: string,
    strokeDashArray: string | null,
    strokeDashOffset: string | null,

    // fill options
    drawFill: boolean,
    fillColor: string,
    fillOpacity: number,

    // marker options
    drawMarker: boolean,
    markerIcon: string, // relative path
    markerIconOpacity: number,
    markerBackgroundColor: string,
    markerBackgroundOpacity: number,
    markerSize: number,

    // circle options
    drawCircle: boolean,
    circleRadius: number,
    circleStrokeColor: string,
    circleStrokeWeight: number,
    circleStrokeOpacity: number,
    circleStrokeLineJoin: string,
    circleStrokeLineCap: string,
    circleStrokeDashArray: string | null,
    circleStrokeDashOffset: string | null,
    circleFillColor: string,
    circleFillOpacity: number,

}

export async function getStyleById(styleId: string): Promise<Style | null> {
    const query = `
        query ($id: UUID!) {
            style(id: $id) {
                drawStroke
                strokeColor
                strokeWeight
                strokeOpacity
                strokeLineJoin
                strokeLineCap
                strokeDashArray
                strokeDashOffset
                drawFill
                fillColor
                fillOpacity
                drawMarker
                markerIcon
                markerIconOpacity
                markerBackgroundColor
                markerBackgroundOpacity
                markerSize
                drawCircle
                circleRadius
                circleFillColor
                circleFillOpacity
                circleStrokeColor
                circleStrokeDashArray
                circleStrokeDashOffset
                circleStrokeLineCap
                circleStrokeLineJoin
                circleStrokeOpacity
                circleStrokeWeight
            }
        }
    `;
    const response = await executeQuery(
        JSON.stringify({
            query,
            variables: {
                id: styleId
            }
        })
    );
    const style: Style | null = response.data.style;
    return style;
}

export interface MapData{
    geojson: string | null,
    providerState: "GEOJSON" | "OPEN_GREEN_MAP" | "GEOTIFF" | "UNSET",
}

export async function getMapDataById(mapDataId: string): Promise<MapData | null>{
    const query = `
        query ($id: UUID!) {
            mapData(id: $id) {
                geojson
                providerState
            }
        }
    `;
    const response = await executeQuery(
        JSON.stringify({
            query,
            variables: {
                id: mapDataId
            }
        })
    );
    const mapData: MapData | null = response.data.mapData;
    return mapData;
}
