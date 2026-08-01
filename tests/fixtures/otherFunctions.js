function focusFunction(){
    document.getElementById("menuNameWifiSTA").scrollIntoView();
}

function removeSelectOptions(selectElement) {
  var i, L = selectElement.options.length - 1;
  for(i = L; i >= 0; i--) {
     selectElement.remove(i);
  }
}

function addSelectOptions(selectElement, text, value){
  var c = document.createElement("option");
  c.text = text;
  c.value = value;
  selectElement.options.add(c, 1);
}


function isArray(ob) {
    return ob.constructor === Array;
}

function remove(array, element){
  var index = array.indexOf(element);
  if (index > -1) {
      array.splice(index, 1);
  }
}

function GoHome(){
    document.location.href="/";
}

// Seconds to string
function secondsToStr(seconds) { // day, h, m and s
    var days = Math.floor(seconds / (24 * 60 * 60));
    seconds -= days * (24 * 60 * 60);
    var hours = Math.floor(seconds / (60 * 60));
    seconds -= hours * (60 * 60);
    var minutes = Math.floor(seconds / (60));
    seconds -= minutes * (60);
       
    return (hours < 10 ? '0' : '') + hours + ":" + (minutes < 10 ? '0' : '') +
    minutes + ":" + (seconds < 10 ? '0' : '') + seconds;;
}

// Strin to minutes
function stringToMinutes(str) { // day, h, m and s
    return (parseInt(str.substring(0, 2),10) * 60) + parseInt(str.substring(3),10);
}

// String to boolean
function stringToBoolean(string) {
    switch (string.toLowerCase().trim()) {
        case "true":
        case "yes":
        case "1":
            return true;
        case "false":
        case "no":
        case "0":
        case null:
            return false;
        default:
            return Boolean(string);
    }
}

function isASCII(str, extended) {
  return (extended ? /^[\x00-\xFF]*$/ : /^[\x00-\x7F]*$/).test(str);
}

// Get Bit
function getBit(number, bitPosition) {
  return (number & (1 << bitPosition)) === 0 ? 0 : 1;
}

// Set Bit
function setBit(number, bitPosition) {
  return number | (1 << bitPosition);
}

// Clear Bit
function clearBit(number, bitPosition) {
  const mask = ~(1 << bitPosition);
  return number & mask;
}

//Update Bit
function updateBit(number, bitPosition, bitValue) {
  const bitValueNormalized = bitValue ? 1 : 0;
  const clearMask = ~(1 << bitPosition);
  return (number & clearMask) | (bitValueNormalized << bitPosition);
}


function updateElemContentStr(data, propertyName, element, label = '') {
  // ÐÑÐ¾Ð²ÐµÑÑÐµÐ¼, ÐµÑÑÑ Ð»Ð¸ ÑÐ²Ð¾Ð¹ÑÑÐ²Ð¾ Ð² Ð¾Ð±ÑÐµÐºÑÐµ dataMain
  if (data.hasOwnProperty(propertyName)) {
      // ÐÑÐ¿Ð¾Ð»ÑÐ·ÑÐµÐ¼ ÐºÐ²Ð°Ð´ÑÐ°ÑÐ½ÑÐµ ÑÐºÐ¾Ð±ÐºÐ¸ Ð´Ð»Ñ Ð´Ð¸Ð½Ð°Ð¼Ð¸ÑÐµÑÐºÐ¾Ð³Ð¾ Ð´Ð¾ÑÑÑÐ¿Ð° Ðº ÑÐ²Ð¾Ð¹ÑÑÐ²Ð°Ð¼
      if (EVSE[propertyName] != data[propertyName]) {
          EVSE[propertyName] = data[propertyName];
          element.innerHTML = label + EVSE[propertyName];
      }
  }
}