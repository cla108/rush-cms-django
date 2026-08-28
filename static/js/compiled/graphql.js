class a extends Error{constructor(e){super(e)}}async function o(r){const e=await fetch("/graphql/",{method:"POST",headers:{"Content-Type":"application/json",Accept:"application/json"},body:r}),t=await e.json();if(e.status!==200)throw t.errors===null||t.errors===void 0?new a("GraphQL response code ("+e.status+") is not 200 but no errors were sent back in the response!"):new a(JSON.stringify(t.errors));return t}async function i(r){return(await o(JSON.stringify({query:`
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
    `,variables:{id:r}}))).data.style}async function n(r){return(await o(JSON.stringify({query:`
        query ($id: UUID!) {
            mapData(id: $id) {
                geojson
                providerState
            }
        }
    `,variables:{id:r}}))).data.mapData}export{n as a,i as g};
