import{l as m,g as h}from"./utils/math.js";import{g as v}from"./graphql.js";import{e as O,a as w}from"./utils/timing.js";function S(t,o){let n=!1;const{x:r,y:i}=t;for(let l=0,e=o.length-1;l<o.length;e=l++){const c=o[l].x,s=o[l].y,u=o[e].x,a=o[e].y;s>i!=a>i&&r<(u-c)*(i-s)/(a-s)+c&&(n=!n)}return n}function C(t,o){if(o<=0)return[];const n=Math.min(...t.map(a=>a.x)),r=Math.max(...t.map(a=>a.x)),i=Math.min(...t.map(a=>a.y)),l=Math.max(...t.map(a=>a.y)),e=o*2,c=e*(Math.sqrt(3)/2),s=[];let u=0;for(let a=i+o;a<=l-o+e;a+=c,u++){const d=u%2*o;for(let p=n+o+d;p<=r+e;p+=e){const k=new m.Point(p,a);S(k,t)&&s.push(k)}}return s}function F(t){let o="";for(let n of t)o+=n.x+","+n.y+" ";return o}function $(t){const r=t.markerOptions.markerSize,i=Math.sqrt(Math.pow(r/2,2)+Math.pow(r/2,2)),l=[new m.Point(40,40),new m.Point(200,80),new m.Point(280,160),new m.Point(120,240),new m.Point(40,160)];let e=`
    <svg
        width="400px"
        height="400px"
        xmlns="http://www.w3.org/2000/svg"
    >
    <polygon 
        points="${F(l)}"
    `;t.drawStroke&&(e+=`
            stroke="${t.strokeOptions.color}"
            stroke-width="${t.strokeOptions.weight}"
            stroke-opacity="${t.strokeOptions.opacity}"
            stroke-linecap="${t.strokeOptions.lineCap}"
            stroke-linejoin="${t.strokeOptions.lineJoin}"
            stroke-dasharray="${t.strokeOptions.dashArray}"
            stroke-dashoffset="${t.strokeOptions.dashOffset}"
        `),t.drawFill?e+=`
            fill="${t.fillOptions.color}"
            fill-opacity="${t.fillOptions.opacity}"
        `:e+='fill="none"',e+="/>";const c=h(l);if(t.drawMarker&&(e+=`
        <circle 
            id="marker-centroid"
            r="${i}px"
            fill=${t.markerOptions.bgColor}
            opacity=${t.markerOptions.bgOpacity}
            cx=${c.x}
            cy=${c.y}
        />
        `),t.drawCircle){const a=5+t.circleOptions.radius/250*65,d=C(l,a),p=`
            r="${a}"
            stroke="${t.circleOptions.strokeColor}"
            stroke-width="${t.circleOptions.strokeWeight}"
            stroke-opacity="${t.circleOptions.strokeOpacity}"
            stroke-linecap="${t.circleOptions.strokeLineCap}"
            stroke-linejoin="${t.circleOptions.strokeLineJoin}"
            stroke-dasharray="${t.circleOptions.strokeDashArray}"
            stroke-dashoffset="${t.circleOptions.strokeDashOffset}"
            fill="${t.circleOptions.fillColor}"
            fill-opacity="${t.circleOptions.fillOpacity}"
        `;for(const k of d)e+=`<circle cx="${k.x}" cy="${k.y}" ${p}/>`}return e+="</svg>",t.drawMarker&&t.markerOptions.data!==null&&(e+=`
        <img 
            id="marker-image"
            src="${t.markerOptions.data}"
            width="${r}"
            height="${r}"
            style='
                position: absolute;
                left: ${c.x-r/2}px;
                top: ${c.y-r/2}px;
                opacity: ${t.markerOptions.markerOpacity}
            '
        />'
        `),e}function y(t){let o=t.parentElement;for(;o!==null&&!o.classList.contains("form-row");)o=o.parentElement;return o}function f(t,o,n){var i;(i=y(o))==null||i.style.setProperty("background-color","#FFFFFF");for(let l of N(t,n)){const e=y(l);e!==null&&(e.style.display="none")}}function _(t,o,n){var i;(i=y(o))==null||i.style.setProperty("background-color","#E2DBC4");for(let l of N(t,n)){const e=y(l);e!==null&&(e.style.display="block")}}function N(t,o){let n=[];for(let r of o)r.groupName===t&&r.el!==null&&n.push(r.el);return n}function g(t){return new Promise((o,n)=>{const r=new FileReader;r.onload=()=>o(r.result),r.onerror=()=>n(r.error),r.readAsDataURL(t)})}document.addEventListener("DOMContentLoaded",()=>{(async()=>{var l;const t=O("style_preview"),o=O("injected-style-id").innerHTML,n=O("injected-media-url").innerHTML;w(document,".field-style_preview");let r={drawStroke:!1,drawFill:!1,drawMarker:!1,drawCircle:!1,strokeOptions:{color:"#FFFFFF",opacity:1,weight:1,lineJoin:"",lineCap:"ROUND",dashArray:"",dashOffset:"0"},fillOptions:{color:"#FFFFFF",opacity:1},markerOptions:{bgColor:"#FFFFFF",bgOpacity:1,data:null,markerOpacity:1,markerSize:22},circleOptions:{radius:50,strokeColor:"#3388FF",strokeWeight:3,strokeOpacity:1,strokeLineJoin:"",strokeLineCap:"ROUND",strokeDashArray:"",strokeDashOffset:"0"}};const i=[{groupName:"Toggle",el:document.querySelector("#id_draw_stroke"),update:e=>{e.checked?_("Stroke",e,i):f("Stroke",e,i),r.drawStroke=e.checked},eventName:"input"},{groupName:"Toggle",el:document.querySelector("#id_draw_fill"),update:e=>{e.checked?_("Fill",e,i):f("Fill",e,i),r.drawFill=e.checked},eventName:"input"},{groupName:"Toggle",el:document.querySelector("#id_draw_marker"),update:e=>{e.checked?_("Marker",e,i):f("Marker",e,i),r.drawMarker=e.checked},eventName:"input"},{groupName:"Toggle",el:document.querySelector("#id_draw_circle"),update:e=>{e.checked?_("Circle",e,i):f("Circle",e,i),r.drawCircle=e.checked},eventName:"input"},{groupName:"Stroke",el:document.querySelector("#id_stroke_color"),update:e=>r.strokeOptions.color=e.value,eventName:"input"},{groupName:"Stroke",el:document.querySelector("#id_stroke_weight"),update:e=>r.strokeOptions.weight=Number(e.value),eventName:"input"},{groupName:"Stroke",el:document.querySelector("#id_stroke_opacity"),update:e=>r.strokeOptions.opacity=Number(e.value),eventName:"input"},{groupName:"Stroke",el:document.querySelector("#id_stroke_line_cap"),update:e=>r.strokeOptions.lineCap=e.value,eventName:"input"},{groupName:"Stroke",el:document.querySelector("#id_stroke_line_join"),update:e=>r.strokeOptions.lineJoin=e.value,eventName:"input"},{groupName:"Stroke",el:document.querySelector("#id_stroke_dash_array"),update:e=>r.strokeOptions.dashArray=e.value,eventName:"input"},{groupName:"Stroke",el:document.querySelector("#id_stroke_dash_offset"),update:e=>r.strokeOptions.dashOffset=e.value,eventName:"input"},{groupName:"Fill",el:document.querySelector("#id_fill_color"),update:e=>r.fillOptions.color=e.value,eventName:"input"},{groupName:"Fill",el:document.querySelector("#id_fill_opacity"),update:e=>r.fillOptions.opacity=Number(e.value),eventName:"input"},{groupName:"Marker",el:document.querySelector("#id_marker_icon"),update:async e=>{let c=null;if(e.files&&(c=e.files[0]),c){const s=await g(c);r.markerOptions.data=s}else if(o!==""){const s=await v(o);if(s!==null){const u=n+s.markerIcon,d=await(await fetch(u)).blob(),p=await g(d);r.markerOptions.data=p}}else r.markerOptions.data=null},eventName:"change"},{groupName:"Marker",el:document.querySelector("#id_marker_icon_opacity"),update:e=>r.markerOptions.markerOpacity=Number(e.value),eventName:"input"},{groupName:"Marker",el:document.querySelector("#id_marker_background_color"),update:e=>r.markerOptions.bgColor=e.value,eventName:"input"},{groupName:"Marker",el:document.querySelector("#id_marker_background_opacity"),update:e=>r.markerOptions.bgOpacity=Number(e.value),eventName:"input"},{groupName:"Marker",el:document.querySelector("#id_marker_size"),update:e=>{r.markerOptions.markerSize=Number(e.value)},eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_stroke_color"),update:e=>r.circleOptions.strokeColor=e.value,eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_radius"),update:e=>r.circleOptions.radius=Number(e.value),eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_stroke_weight"),update:e=>r.circleOptions.strokeWeight=Number(e.value),eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_stroke_opacity"),update:e=>r.circleOptions.strokeOpacity=Number(e.value),eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_stroke_line_cap"),update:e=>r.circleOptions.strokeLineCap=e.value,eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_stroke_line_join"),update:e=>r.circleOptions.strokeLineJoin=e.value,eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_stroke_dash_array"),update:e=>r.circleOptions.strokeDashArray=e.value,eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_stroke_dash_offset"),update:e=>r.circleOptions.strokeDashOffset=e.value,eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_fill_color"),update:e=>r.circleOptions.fillColor=e.value,eventName:"input"},{groupName:"Circle",el:document.querySelector("#id_circle_fill_opacity"),update:e=>r.circleOptions.fillOpacity=Number(e.value),eventName:"input"}];for(let e of i){const c=async()=>{e.el!==null&&(await e.update(e.el),t.innerHTML=$(r))};(l=e==null?void 0:e.el)==null||l.addEventListener(e.eventName,c),await c()}})()});
