var geocoder;
var map;
var config = require('../config.js');
var mykey = config.MY_KEY;
var secretkey = config.SECRET_KEY;
var map;
var iconBase = 'http://maps.google.com/mapfiles/ms/icons';
var markerBounds;

//function getCookie(name) {
//    var cookieValue = null;
//    if (document.cookie && document.cookie !== '') {
//        var cookies = document.cookie.split(';');
//        for (var i = 0; i < cookies.length; i++) {
//            var cookie = jQuery.trim(cookies[i]);
//            // Does this cookie string begin with the name we want?
//            if (cookie.substring(0, name.length + 1) === (name + '=')) {
//                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
//                break;
//            }
//        }
//    }
//    return cookieValue;
//}
//var csrftoken = getCookie('csrftoken');

//function initMap() {
//    map = new google.maps.Map(document.getElementById('map'), {
//      zoom: 12,
//      center: {lat: -26.2041, lng: 28.0473}
//    });
//
//    var markerIcon = 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
//    newMarkerOnMap(potentialAddresses, markerIcon)
//
//  }

//function geocodeAddress(geocoder, resultsMap, markerIcon) {
//
//    var address = document.querySelector('#address').value;
//    var rent = document.querySelector('#rent').value;
//    var markerIcon = 'http://maps.google.com/mapfiles/ms/icons/red-dot.png'
//    var currAddress = address
//
//    var loc = []
//    geocoder.geocode({'address': currAddress}, function(results, status) { //Address to lat/lon
//      if (status === 'OK') {
//        loc[0]=results[0].geometry.location.lat();
//        loc[1]=results[0].geometry.location.lng();
//        resultsMap.setCenter(results[0].geometry.location);
//
//        // Place a new marker
//        var marker = new google.maps.Marker({
//          map: resultsMap,
//          position: results[0].geometry.location,
//          icon : markerIcon
//        });
//
//        //Post data
//        var data = {'currentAddress': currAddress, 'rent':rent, 'latitude': loc[0], 'longitude': loc[1],
//        'csrfmiddlewaretoken': csrftoken};
//        $.post("", data, function(response){
//        console.log('done1')
//        });
//
//      } else {
//        alert('Geocode was not successful for the following reason: ' + status);
//      }
//    });
//}

function centralMap(){
    map = new google.maps.Map(document.getElementById('map'), {
      zoom: 12,
      center:  {lat: -26.2041, lng: 28.0473}
    });

    markerBounds = new google.maps.LatLngBounds();

    markerBounds = newMarkerOnMap(potentialAddresses,map,'/grn-pushpin.png', markerBounds)
    markerBounds = newMarkerOnMap(collectionAddresses, map,'/red-pushpin.png',markerBounds)

    map.fitBounds(markerBounds)
}

function newMarkerOnMap(addr, currMap, marker, bounds){
    var array = JSON.parse("[" + addr + "]");
    var iconChoice = iconBase + marker;
    for (var i=0; i<array[0].length;i++){
        var currPos = array[0][i];
        var lat_temp = parseFloat(currPos[0]);
        var lng_temp = parseFloat(currPos[1]);
        var pos = new google.maps.LatLng(lat_temp, lng_temp);
        var marker = new google.maps.Marker({
        map: currMap,
        position: pos,
        icon: iconChoice,
        });
        bounds.extend(pos)
    }
    return bounds
}