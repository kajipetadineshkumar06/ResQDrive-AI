// =====================================
// CREATE MAP
// =====================================

const map = L.map("map").setView(
    [17.385044, 78.486671],
    15
);


// =====================================
// OPEN STREET MAP
// =====================================

L.tileLayer(
    "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
        attribution:
            "&copy; OpenStreetMap Contributors"
    }
).addTo(map);


// =====================================
// USER LOCATION (Emergency)
// =====================================

const userLatitude = 17.385044;
const userLongitude = 78.486671;

const userMarker = L.marker(
    [
        userLatitude,
        userLongitude
    ]
).addTo(map);

userMarker.bindPopup(
    "🚨 Emergency Location"
).openPopup();


// =====================================
// PROVIDER MARKER
// =====================================

let providerMarker = null;


// =====================================
// CONNECT TO FASTAPI WEBSOCKET
// =====================================

const socket = new WebSocket(
    "ws://127.0.0.1:8000/ws/tracking/5"
);


// =====================================
// WHEN CONNECTED
// =====================================

socket.onopen = () => {

    console.log(
        "✅ Connected to ResQDrive WebSocket"
    );

};


// =====================================
// RECEIVE LIVE LOCATION
// =====================================

socket.onmessage = (event) => {

    const data = JSON.parse(
        event.data
    );

    console.log(
        "Live Update:",
        data
    );


    if (
        data.event === "provider_location"
    ) {

        const latitude = data.latitude;

        const longitude = data.longitude;


        // First time create marker

        if (providerMarker === null) {

            providerMarker = L.marker(
                [
                    latitude,
                    longitude
                ]
            ).addTo(map);

            providerMarker.bindPopup(
                "🚗 Service Provider"
            );

        }

        // Move marker

        else {

            providerMarker.setLatLng(
                [
                    latitude,
                    longitude
                ]
            );

        }


        // Keep provider centered

        map.panTo(
            [
                latitude,
                longitude
            ]
        );

    }

};


// =====================================
// DISCONNECTED
// =====================================

socket.onclose = () => {

    console.log(
        "❌ WebSocket Closed"
    );

};


// =====================================
// ERROR
// =====================================

socket.onerror = (error) => {

    console.log(
        "WebSocket Error",
        error
    );

};