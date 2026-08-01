let ignoreCount = 0;
let needInit = 1;
let mainTimer = 0;
let allowDataSending = true;



class Debouncer {
    constructor(name, inputTimer, ignoreFlag, timeout) {
        this.name = name;
        this.inputTimer = inputTimer;
        this.ignoreFlag = ignoreFlag;
        this.timeout = timeout;
        this.value = 0;
    }
    
    doneInput()
    {
        postPageEvent(this.name, parseInt(this.value));
        this.ignoreFlag = 0;
    }

    txData(value)
    {
        this.value = value;
        
        clearTimeout(this.inputTimer);
        this.inputTimer = setTimeout(this.doneInput.bind(this), this.timeout);
        this.ignoreFlag = 1;
    }
}

let Debounce = {
    currentSet  : new Debouncer("currentSet", 0, 0,100),
    energyLimit : new Debouncer("energyLimit", 0, 0, 100),
    timeLimit   : new Debouncer("timeLimit", 0, 0, 100),
    moneyLimit  : new Debouncer("moneyLimit", 0, 0, 100),
    aiVoltage   : new Debouncer("aiVoltage", 0, 0, 100),
    imbDeltaMax : new Debouncer("imbDeltaMax", 0, 0, 100),

    sh1CurrentValue   : new Debouncer("sh1CurrentValue", 0, 0, 100),
    sh2CurrentValue   : new Debouncer("sh2CurrentValue", 0, 0, 100),
    sh1EnergyValue   : new Debouncer("sh1EnergyValue", 0, 0, 100),
    sh2EnergyValue   : new Debouncer("sh2EnergyValue", 0, 0, 100),
};

// Confirms  states
const Started   = 1;
const InProgess = 2;
const Finished  = 3;

var stateApConf   = Finished;
var stateStaConf  = Finished;
var statePageConf = Finished;
var TOApConf   = null;
var TOStaConf  = null;
var TOPageConf = null;

var counterAResetConf = Finished;
var counterBResetConf = Finished;
var factoryResetConf  = Finished;
var TOAResetConf = null;
var TOBResetConf = null;
var TOFResetConf = null;

/*-----------------------------------------------------------------------------------------*/
/*                                  DOM Variables                                          */
/*-----------------------------------------------------------------------------------------*/ 
let
    /* Tabs */
    dataList   = document.getElementsByClassName("dataList"),
    tab        = document.querySelectorAll(".info-header-tab"),
    info       = document.querySelector(".info-header"),
    tabContent = document.querySelectorAll(".info-tabcontent"),

    
    /* Main *///-----------------------------------------------
    statusValue = document.querySelectorAll('[id=status-value]'),
    subStatusValue  = document.getElementById('subStatus-value'),

    
    pilotValue   = document.getElementById('pilot-value'),

    voltageValue =  document.querySelectorAll('[id=voltage-value]'),

    currentValue =  document.querySelectorAll('[id=current-value]'),

    powerValue =  document.querySelectorAll('[id=power-value]'),

    temperatureBoxValue    = document.getElementById('temperatureBox-value'),
    temperatureSocketValue = document.getElementById("temperatureSocket-value"),
    sessionEnergyValue     = document.getElementById('session-energy-value'),
    sessionTimeValue  = document.getElementById('session-time-value'),
    sessionMoneyValue = document.getElementById('session-money-value'), 
    totalEnergyValue  = document.getElementById('total-energy-value'),

    /* Independed counters */
    IEM1Value = document.getElementById('IEM-1-value'),
    IEM1Money = document.getElementById('IEM-1-money'),
    IEM2Value = document.getElementById('IEM-2-value'),
    IEM2Money = document.getElementById('IEM-2-money'),
    btnResetIEM1 = document.getElementById("btn-IEM-1"),
    btnResetIEM2 = document.getElementById("btn-IEM-2"),

    
    //switchControlPE    = document.getElementById('controlPE'),
    rangeSliderCurrent = document.getElementById('current-limit'),

    //currentLimitValue  = document.getElementById('maxcurrent-value'),
    currentLimitValue =  document.querySelectorAll('[id=maxcurrent-value]'),
    
    switchEvseEnabled  = document.getElementById('evseEnabled'),
    switchAdapterChange = document.getElementById('adapterEnabled'),
    adapterSection = document.getElementById('adapterSection'),
    
    /* AI */
    switchAIMode  = document.getElementById('AIMode'),
    AIModeSelect =  document.getElementById('AIModeSelect'),
    rangeSliderAIVoltage = document.getElementById('voltage-adaptive'),
    AIvoltageValue       = document.getElementById('voltage-adaptive-value'),

    AIVoltageBlock = document.getElementById('adaptation-voltage-block'),
    AIPowerBlock = document.getElementById('adaptation-power-block'),
    AIAutoBlock = document.getElementById('adaptation-auto-block'),

    AIVoltageStart = document.getElementById('voltage-start-val'),
    AIVoltageDrop = document.getElementById('voltage-drop-val'),

    AIPowerDrop = document.getElementById('power-drop-val'),

    phaseImbalaceBlock = document.getElementById('phase-imbalance-block'),
    switch3PControl = document.getElementById('3PImbalance'),
    ThreePhaseBalanceBlockSlider = document.getElementById('3P-delta-slider-block'),
    range3PControl = document.getElementById('3p-delta'),
    phase3Value = document.getElementById('3p-max-delta'),
    
     /* ~AI */

    
    controlPEValue = document.getElementById('controlPE-value'),
    leakValue      = document.getElementById("leak-value"),
    /* ~Main *///-----------------------------------------------
   
   
    /* Timer */
    /* Suspend limits*/
    switchSuspendLimits    = document.getElementById("suspend-limits-switch"),
    //switchSuspendErrors    = document.getElementById("suspend-errors-switch"),
    switchOneCharge        = document.getElementById("suspend-one-charge-switch"),
    
    /* Limits */
    // time
    switchTimeLimit      = document.getElementById("isTimeLimit"),
    timeLimitValue       = document.getElementById("time-limit-value"),
    rangeSliderTimeLimit = document.getElementById("time-limit"),
    
    // energy
    switchEnergyLimit      = document.getElementById("isEnergyLimit"),
    energyLimitValue       = document.getElementById("energy-limit-value"),
    energyLimitTimeValue   = document.getElementById("energy-limit-time-value"),
    rangeSliderEnergyLimit = document.getElementById("energy-limit"),
    
    // money
    switchMoneyLimit      = document.getElementById("isMoneyLimit"),
    moneyLimitValue       = document.getElementById("money-limit-value"),
    rangeSliderMoneyLimit = document.getElementById("money-limit"),
    
    // tarif
    tarif_1 = document.getElementById("tarif-1-value"),
    activeTarif = document.querySelectorAll('[id=usedTarif]'),

    tarifAValue = document.getElementById("tarif-A-value"),
    tarifAEnable = document.getElementById("tarif-A-switch"),
    tarifAStart = document.getElementById("tarif-A-start"),
    tarifAStop = document.getElementById("tarif-A-stop"),

    tarifBValue = document.getElementById("tarif-B-value"),
    tarifBEnable = document.getElementById("tarif-B-switch"),
    tarifBStart = document.getElementById("tarif-B-start"),
    tarifBStop = document.getElementById("tarif-B-stop"),

    
    /* Schedule1 */
    sch1_content    =  document.getElementById("sch-1-content"),
    switchSchedule1 =  document.getElementById("sch-1-switch"),
    startSchedule1  = document.getElementById("sch-1-start-time"),
    stopSchedule1   = document.getElementById("sch-1-stop-time"),
    // current
    sch1_range_slider_current = document.getElementById('sch-1-current-limit'),
    sch1_current_limit_value  = document.getElementById('sch-1-current-limit-value'),
    sch1_switch_current       = document.getElementById("is-sch-1-current-limit"),
    // energy
    sch1_range_slider_energy = document.getElementById('sch-1-energy-limit'),
    sch1_energy_limit_value  = document.getElementById('sch-1-energy-limit-value'),
    sch1_switch_energy       = document.getElementById("is-sch-1-energy-limit"),
    
    /* Schedule2 */
    sch2_content    = document.getElementById("sch-2-content"),
    switchSchedule2 = document.getElementById("sch-2-switch"),
    startSchedule2  = document.getElementById("sch-2-start-time"),
    stopSchedule2   = document.getElementById("sch-2-stop-time"),
    // current
    sch2_range_slider_current = document.getElementById('sch-2-current-limit'),
    sch2_current_limit_value  = document.getElementById('sch-2-current-limit-value'),
    sch2_switch_current       = document.getElementById("is-sch-2-current-limit"),
    // energy
    sch2_range_slider_energy = document.getElementById('sch-2-energy-limit'),
    sch2_energy_limit_value  = document.getElementById('sch-2-energy-limit-value'),
    sch2_switch_energy       = document.getElementById("is-sch-2-energy-limit"),

    // Charge now
    chargeNow = document.getElementById("chargeNow"),
    /* ~Timer */

    /* Settings */
    /* WiFi Settings */
    localIpValue = document.getElementById("local_IP");
    ESP_MACValue = document.getElementById("ESP_MAC");
    nameAP = document.getElementById("ssidNameAP"),

    passwordAP = document.getElementById("ssidPasswordAP"),
    togglePassword = document.getElementById("togglePassword"),
    eyeOpenIconPass = document.getElementById("eye-icon-open"),
    eyeCloseIconPass = document.getElementById("eye-icon-closed"),

    passwordAPConf = document.getElementById("ssidPasswordAPConfirm"),
    togglePasswordConf = document.getElementById("togglePasswordConf"),
    eyeOpenIconPassConf = document.getElementById("eye-icon-open-pass-conf"),
    eyeCloseIconPassConf = document.getElementById("eye-icon-closed-pass-conf"),

    netPassword = document.getElementById("ssidPassword"),
    toggleNetPassword = document.getElementById("toggleSsidPassword"),
    eyeOpenIconNetPass = document.getElementById("eye-icon-open-pass-net");
    eyeCloseIconNetPass = document.getElementById("eye-icon-closed-pass-net");

    httpPassword = document.getElementById("httpPassword"),
    toggleHttpPassword = document.getElementById("toggleHttpPassword"),
    eyeOpenIconHttpPass = document.getElementById("eye-icon-open-pass-http"),
    eyeCloseIconHttpPass = document.getElementById("eye-icon-closed-pass-http"),

    httpPasswordConf = document.getElementById("httpPasswordConfirm"),
    toggleHttpPasswordConf = document.getElementById("toggleHttpPasswordConfirm"),
    eyeOpenIconHttpPassConf = document.getElementById("eye-icon-open-pass-http-conf"),
    eyeCloseIconHttpPassConf = document.getElementById("eye-icon-closed-pass-http-conf"),



    netName = document.getElementById("ssidName"),

 
    // netPasswordConf = document.getElementById("ssidPasswordConfirm"),
    
    httpName = document.getElementById("httpName"),
 
   
    switchWifiMode = document.getElementById("netWifiMode"),

    /* Mac bind*/
    switch_mac_bind = document.getElementById("bind-MAC"),
    STA_MAC_value = document.getElementById("STA-MAC");
    
    /* WiFi scan */
    btnScanNet    = document.getElementById("scanNet"),
    btnSaveNetSet = document.getElementById("btnSaveNet"),
    btnSaveAPSet = document.getElementById("btnSaveAP"),
    btnSaveHttpSet = document.getElementById("btnSaveHttp"),
    btnSaveRates  = document.getElementById("btnSaveRates"),
    txtlistNets   = document.getElementById("textNetList"),
    txtNameNet    = document.getElementsByClassName("nameNet"),
    txtNameMAC    = document.getElementsByClassName("nameMAC"),
    
    /* Logs */
     txtlistLogs = document.getElementById("textLogs"),
    // btnGetLog   = document.getElementById("getLog"),

    /* Other */
    timerTypeValue = document.getElementById("timerType"),
    languageValue = document.getElementById("lang"),
    minVoltageValue = document.getElementById("minVoltage"),

    /* VersionFW */
    verFWMain = document.getElementById("verFWMain"),
    verFWWifi = document.getElementById("verFWWifi"),

    /* Id */
    serialNum = document.getElementById("serialNum"),

    /* Time */
    systemTime = document.getElementById("systemTime"),
    btnGetTime = document.getElementById("btn-getTime"),
    
    timeZoneValue=document.getElementById("timeZone"),
    ocppEnabled = document.getElementById("ocppEnabled"),
    ocppOfflineAva = document.getElementById("ocppOfflineAva"),
    ocppConnected = document.getElementById("ocppConnected"),

    /* Factory reset */
    btnFactoryReset = document.getElementById("btn-factoryReset"),
    switchBroadcastMode = document.getElementById("broadcastMode"),


    // ocppVendor = document.getElementById("ocppVendor"),
    // chargeLab = document.getElementById("chargeLab"),
    // selectCustomOCPPprovider = document.getElementById("selectCustomOCPPprovider"),  
    // linkToApp = document.getElementById("linkToApp"),
    // cmodalOverlay = document.getElementById("modalOverlay"),
    // popupSave = document.getElementById('popupSave'),
    // popupCancel = document.getElementById('popupCancel'),


  //  btnFwUpdate = document.getElementById("btnFwUpdate"),
    OCPPConfigBlock = document.getElementById('OCPP-config-block'),
    btnOCPPConfig = document.getElementById("btnOCPPConfig");

    /* ~Settings */

/* ~DOM Variables */

let lastSelectedIndex = 0; 
// let lastSelectedIndexCancel = 0;
/* Charts */
let data = {
    labels: ['Voltage, V'],
    series: [ [], [], [] ]
},
data2 = {
    labels: ['Current, A'],
    series: [ [], [], [] ]
},
data3 = {
    labels: ['Temperature, C'],
    series: [ [], [], [] ]
},
conf = {
    showPoint: false,
    low: 100,
    showArea: true,
},
confT = {
    showPoint: false,
    showArea: true,
    axisY : { referenceValue: 0 }  
},
chart1 = new Chartist.Line('#gridVoltage', data, conf),
chart2 = new Chartist.Line('#current', data2, conf),
chart3 = new Chartist.Line("#temps",data3,confT);



window.addEventListener("offline", function() {     
    ShowOfflineBar(); 
}); 

window.addEventListener("online", function() {     
    HideOfflineBar(); 
});

/*-----------------------------------------------------------------------------------------*/
/*                                      Init  onLoad <DOM>                                   */
/*                             Starts event listeners and setintervals                      */
/*-----------------------------------------------------------------------------------------*/ 


window.addEventListener("DOMContentLoaded", function() {
    'use strict';

    /* Main handler */
    mainTimer = setInterval(function () { postDataMain();}, 1000);
    postDataMain();

    /* Charts handler */
    setInterval(() => {
            data.series[0].push(EVSE.voltMeas1);
        if(EVSE.voltMeas2 > 0)
            data.series[1].push(EVSE.voltMeas2);
        if(EVSE.voltMeas3 > 0)
            data.series[2].push(EVSE.voltMeas3);
        
        if (data.series[0].length > 100) {
            data.series[0].shift();
            data.series[1].shift();
            data.series[2].shift();
        }
         
        data2.series[0].push(EVSE.curMeas1);
        data2.series[1].push(EVSE.curMeas2);
        data2.series[2].push(EVSE.curMeas3);

        if (data2.series[0].length > 100) {
            data2.series[0].shift();
            data2.series[1].shift();
            data2.series[2].shift();
        }
        
        data3.series[0].push(EVSE.temp1);
        data3.series[1].push(EVSE.temp2);
       // data3.series[2].push(EVSE.temp1);

        if (data3.series[0].length > 100) {
            data3.series[0].shift();
            data3.series[1].shift();
            data3.series[2].shift();
        }

        chart1.update();
        chart2.update();
        chart3.update();

    }, 1000);

    ocppEnabled.addEventListener("input", function () {
        (ocppEnabled.checked) ? EVSE.ocppEnabled = 1 : EVSE.ocppEnabled = 0;
        postPageOneEvent("ocppEnabled",  EVSE.ocppEnabled);   
    });

    ocppOfflineAva.addEventListener("input", function () {
        (ocppOfflineAva.checked) ? EVSE.ocppOfflineAva = 1 : EVSE.ocppOfflineAva = 0;
        postPageOneEvent("ocppOfflineAva",  EVSE.ocppOfflineAva);   
    });

    /* Current slider handler */
    rangeSliderCurrent.addEventListener("input", function() {
        EVSE.currentSet = rangeSliderCurrent.value;
        if (switchAIMode.checked == true) {

            for(var i = 0; i < currentLimitValue.length; i++)
            { 
                currentLimitValue[i].textContent = EVSE.aiModeCurrent + " /" + EVSE.currentSet;
            }

        }else{

            for(var i = 0; i < currentLimitValue.length; i++)
            { 
                currentLimitValue[i].textContent = EVSE.currentSet;
            }
        }

        Debounce.currentSet.txData(EVSE.currentSet);
    });

    /* Adaptive voltage slider handler */
    rangeSliderAIVoltage.addEventListener('input', function() {
        AIvoltageValue.textContent = rangeSliderAIVoltage.value;
        EVSE.voltageAI = rangeSliderAIVoltage.value;
        
        Debounce.aiVoltage.txData(EVSE.voltageAI);
    });

    range3PControl.addEventListener('input', function() {
        phase3Value.textContent = range3PControl.value;
        EVSE.phase3Value = range3PControl.value;

        Debounce.imbDeltaMax.txData(EVSE.phase3Value);
    });

    
    /* Adaptive switch handler */
    switchAIMode.addEventListener('input', function() {
        if (switchAIMode.checked) 
        {
            AIModeSelect.disabled = false;
            //rangeSliderAIVoltage.disabled = false;

            switch (AIModeSelect.value) {
                case "AI_MODE_1":
                    EVSE.aiMode = 1;
                    AIVoltageBlock.hidden = false;
                    AIPowerBlock.hidden = true;
                    AIAutoBlock.hidden = true;
                    break;
                case "AI_MODE_2":
                    EVSE.aiMode =  2;
                    AIVoltageBlock.hidden = true;
                    AIAutoBlock.hidden = false;
                    AIPowerBlock.hidden = true;
                    break;
                case "AI_MODE_3":
                    EVSE.aiMode = 3;
                    AIVoltageBlock.hidden = true;
                    AIAutoBlock.hidden = true;
                    AIPowerBlock.hidden = false;
                    break;
            }
        } else {
            AIModeSelect.disabled = true;
            //rangeSliderAIVoltage.disabled = false;  
            AIVoltageBlock.hidden = true;
            AIAutoBlock.hidden = true;
            AIPowerBlock.hidden = true;        
            EVSE.aiMode = 0;
        }
        postPageEvent("aiMode", EVSE.aiMode);
    });


    switch3PControl.addEventListener("input", function(){
        if (switch3PControl.checked)
        {
            ThreePhaseBalanceBlockSlider.hidden = true;
            EVSE.phase3Settings = 2;
        }
        else
        {
            ThreePhaseBalanceBlockSlider.hidden = false;
            EVSE.phase3Settings = 0;
        }
        postPageEvent("a_ImbalC", EVSE.phase3Settings);
    });
 
    /* AI type switch handler */
    AIModeSelect.addEventListener("input", function () 
    {
        switch (AIModeSelect.value) 
        {
            case "AI_MODE_1":
                AIVoltageBlock.hidden = false;
                AIPowerBlock.hidden = true;
                AIAutoBlock.hidden = true;
                postPageEvent("aiMode", 1);
                break;
            case "AI_MODE_2":
                AIVoltageBlock.hidden = true;
                AIPowerBlock.hidden = true;
                AIAutoBlock.hidden = false;
                postPageEvent("aiMode", 2);
                break;
            case "AI_MODE_3":
                AIVoltageBlock.hidden = true;
                AIPowerBlock.hidden = false;
                AIAutoBlock.hidden = true;
                postPageEvent("aiMode", 3);
                break;
        }
    });

    /* Evse enabled switch handler */
    switchEvseEnabled.addEventListener('input', function() {  
        if (switchEvseEnabled.checked) {
            EVSE.evseEnabled = 1;
            switchTimeLimit.checked     = 0;
            switchEnergyLimit.checked   = 0;
            switchMoneyLimit.checked    = 0;
            
            EVSE.energyLimit = 0;
            energyLimitValue.textContent = (EVSE.energyLimit).toFixed(3); 
            rangeSliderEnergyLimit.value = (EVSE.energyLimit * 10).toFixed(0);

            EVSE.timeLimit = 0;
            timeLimitValue.textContent = secondsToStr(EVSE.timeLimit); 
            rangeSliderTimeLimit.value = EVSE.timeLimit;

            EVSE.moneyLimit = 0;
            moneyLimitValue.textContent = (EVSE.moneyLimit).toFixed(2); 
            rangeSliderMoneyLimit.value = (EVSE.moneyLimit * 10).toFixed(0);
        } else {
            EVSE.evseEnabled = 0;
        }
        postPageEvent("evseEnabled", EVSE.evseEnabled);
    });


    switchAdapterChange.addEventListener('input', function() {  
        if (switchAdapterChange.checked) {
            EVSE.adapterEnabled = 1;
        } else {
            EVSE.adapterEnabled = 0;
        }
        postPageEvent("adapterEnabled", EVSE.adapterEnabled);
    });


    /*-----------------------------------Change page start-----------------------------------*/
    // function n(e) {
    //     for (let t = e; t < tabContent.length; t++) tabContent[t].classList.add("d-none");
    // }

    // n(1);
    // info.addEventListener("click", function (e) 
    // {
    //         let t = e.target;
    //         console.log(e);
    //         console.log(t);
    //         console.log(t.offsetParent);
    //         console.log(t.offsetParent.offsetParent);



    //         if(t)
    //         {
    //             if (t.classList.contains("info-header-tab")) 
    //             {
    //                 var a;

    //                 for (let i = 0; i < tab.length; i++)
    //                 {
    //                     if(t == tab[i])
    //                     {
    //                         n(0); 
    //                         if(tabContent[(a = i)].classList.contains("d-none"))
    //                         {
    //                             tabContent[a].classList.remove("d-none");
    //                         }
    //                     }
    //                 }
    //             }

    //             if(t.offsetParent.classList.contains("info-header-tab"))
    //             {
    //                 var a;

    //                 for (let i = 0; i < tab.length; i++)
    //                 {
    //                     if(t.offsetParent == tab[i])
    //                     {
    //                         n(0); 
    //                         if(tabContent[(a = i)].classList.contains("d-none"))
    //                         {
    //                             tabContent[a].classList.remove("d-none");
    //                         }
    //                     }
    //                 }
    //             }

    //         }
    // });

    // function changeTab(num)
    // {
    //     n(0); 
    //     if(tabContent[num].classList.contains("d-none"))
    //     {
    //         tabContent[num].classList.remove("d-none");
    //     }
    // }

   

    /*-----------------------------------Change page stop-----------------------------------*/

    /* Event listeners */
    nameAP.addEventListener("input", function () 
    {
        EVSE.ssidNameAP = nameAP.value;
        
    }),
    passwordAP.addEventListener("input", function () 
    {
        EVSE.ssidPasswordAP = passwordAP.value;
    }),
    passwordAPConf.addEventListener("input", function () 
    {
        EVSE.ssidPasswordAPConf = passwordAPConf.value;
    }),

    netName.addEventListener("input", function () 
    {
        (EVSE.ssidName = netName.value);
    }),
    netPassword.addEventListener("input", function () 
    {
        (EVSE.ssidPassword = netPassword.value);
    }),

    httpName.addEventListener("input", function () 
    {
        (EVSE.httpUsername = httpName.value);
    }),
    httpPassword.addEventListener("input", function () 
    {
        (EVSE.httpPassword = httpPassword.value);
    }),
    httpPasswordConf.addEventListener("input", function () 
    {
        (EVSE.httpPasswordConf = httpPasswordConf.value);
    }),
    
    STA_MAC_value.addEventListener("input", function () 
    {
        (EVSE.STA_MAC = STA_MAC_value.value);
    }),

    btnScanNet.addEventListener("click", function () 
    {
        let e = new XMLHttpRequest();
        e.open("POST", "/scan", !0);
        e.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
        e.send();
        EVSE.blockScanResult = false;
        txtlistNets.innerHTML = "Scanning...";      
    }),

    txtlistNets.addEventListener("click", function (e) {
        let t = e.target;
        if (t && t.classList.contains("nameNet"))
        {
            for (let e = 0; e < txtNameNet.length; e++)
            {
                if (t == txtNameNet[e]) 
                {
                    (netName.value = txtNameNet[e].textContent), (netName.textContent = txtNameNet[e].textContent), (EVSE.ssidName = txtNameNet[e].textContent);
                    break;
                }
            }
        }
        if (t && t.classList.contains("nameMAC"))
        {
            for (let e = 0; e < txtNameMAC.length; e++)
            {
                if (t == txtNameMAC[e]) 
                {
                    (STA_MAC_value.value = txtNameMAC[e].textContent), (STA_MAC_value.textContent = txtNameMAC[e].textContent), (EVSE.STA_MAC = txtNameMAC[e].textContent);
                    break;
                }
            }
        }
    }),
    switchWifiMode.addEventListener("input", function () {
        if (switchWifiMode.checked) {
            EVSE.WifiMode = 3; // APSTA
        } else {
            EVSE.WifiMode = 2; //AP
        }
    }),

    switchBroadcastMode.addEventListener("input", function () {
        if (switchBroadcastMode.checked) {
            EVSE.broadcastMode = 0; // AP
            postPageEvent("broadcastMode", 0)
        } else {
            EVSE.broadcastMode = 1; // STA
            postPageEvent("broadcastMode", 1);
        }
    }),
    
    /* MAC bind switch */
    switch_mac_bind.addEventListener("input", function () {
        if (switch_mac_bind.checked) {
            EVSE.mac_bind = 1;
        } else {
            EVSE.mac_bind = 0;
        }
    }),

    togglePassword.addEventListener("click", function () {
        const isPasswordVisible = passwordAP.type === 'text';
        passwordAP.type = isPasswordVisible ? 'password' : 'text';

        // Toggle the icons
        if (isPasswordVisible) {
            eyeOpenIconPass.style.display = '';
            eyeCloseIconPass.style.display = 'none';
        } else {
            eyeOpenIconPass.style.display = 'none';
            eyeCloseIconPass.style.display = '';
        }
    }),
    

    togglePasswordConf.addEventListener("click", function () {

        const isPasswordConfVisible = passwordAPConf.type === 'text';
        passwordAPConf.type = isPasswordConfVisible ? 'password' : 'text';

        if (isPasswordConfVisible) {
            eyeOpenIconPassConf.style.display = '';
            eyeCloseIconPassConf.style.display = 'none';
        } else {
            eyeOpenIconPassConf.style.display = 'none';
            eyeCloseIconPassConf.style.display = '';
        }
    }),

    toggleNetPassword.addEventListener("click", function () {

        const isPasswordVisible = netPassword.type === 'text';
        netPassword.type = isPasswordVisible ? 'password' : 'text';

        if (isPasswordVisible) {
            eyeOpenIconNetPass.style.display = '';
            eyeCloseIconNetPass.style.display = 'none';
        } else {
            eyeOpenIconNetPass.style.display = 'none';
            eyeCloseIconNetPass.style.display = '';
        }
    }),



    toggleHttpPassword.addEventListener("click", function () {

        const isPasswordVisible = httpPassword.type === 'text';
        httpPassword.type = isPasswordVisible ? 'password' : 'text';

        if (isPasswordVisible) {
            eyeOpenIconHttpPass.style.display = '';
            eyeCloseIconHttpPass.style.display = 'none';
        } else {
            eyeOpenIconHttpPass.style.display = 'none';
            eyeCloseIconHttpPass.style.display = '';
        }
    }),




    toggleHttpPasswordConf.addEventListener("click", function () {

        const isPasswordVisible = httpPasswordConf.type === 'text';
        httpPasswordConf.type = isPasswordVisible ? 'password' : 'text';

        if (isPasswordVisible) {
            eyeOpenIconHttpPassConf.style.display = '';
            eyeCloseIconHttpPassConf.style.display = 'none';
        } else {
            eyeOpenIconHttpPassConf.style.display = 'none';
            eyeCloseIconHttpPassConf.style.display = '';
        }
    }),

    /* Save AP WiFi settings */
    btnSaveAPSet.addEventListener("click", function () {
        
        // Every press check input.    
        if(CheckApSettings() == false) 
        {    
            clearTimeout(TOApConf);
            btnSaveAPSet.innerHTML = langHtmlMult.btnNameWifiAPSave[EVSE.language];
            btnSaveAPSet.style.backgroundColor = "#3071A9";

            if( stateApConf == Started)
            {
                stateApConf = Finished;
                this.innerHTML = langHtmlMult.btnNameWifiAPSave[EVSE.language];
                this.style.backgroundColor = "#3071A9";
            }

            return;
        }

        if(stateApConf == Finished)
        {     
          stateApConf = Started;
         
          DisplayErrorMessage("WiFiAPSaveMessage", msg.wifiConfirm, 'Green');
          
          this.innerHTML = langHtmlMult.btnNameWifiAPConf[EVSE.language];
          this.style.backgroundColor = "Green";
          
          clearTimeout(TOApConf);
          TOApConf = setTimeout(function () {

              stateApConf = Finished;
              btnSaveAPSet.innerHTML = langHtmlMult.btnNameWifiAPSave[EVSE.language];
              btnSaveAPSet.style.backgroundColor = "#3071A9";
              DisplayErrorMessage("WiFiAPSaveMessage", "");
          
          }, 10000);

          return;
        }

        if(stateApConf == InProgess) 
        {
            return;
        }

        stateApConf = InProgess;
        
        DisplayErrorMessage("WiFiAPSaveMessage", msg.wifiConfirmAfter, 'Green');
        
        this.innerHTML = langHtmlMult.btnNameWifiAPSave[EVSE.language];
        this.style.backgroundColor = "#3071A9";

        clearTimeout(TOApConf);
        setTimeout(function () {

            stateApConf = Finished;
            DisplayErrorMessage("WiFiAPSaveMessage", "");
       
        }, 10000);

        let e = new XMLHttpRequest();
        e.open("POST", "/configAP", true),
        e.setRequestHeader("Content-type", "application/x-www-form-urlencoded"),
        e.send(
            "ssidNameAP=" +
            encodeURIComponent(EVSE.ssidNameAP) +
            "&ssidPasswordAP=" +
            encodeURIComponent(EVSE.ssidPasswordAP) + 
            "&ssidPasswordAPConf=" +
            encodeURIComponent(EVSE.ssidPasswordAPConf) 
            // "&broadcastMode="+
            // EVSE.broadcastMode 
        ),
        e.onreadystatechange = function() {
            if ((e.readyState == 4) && (e.status == 200)) {
                if(this.responseText.length > 0)
                    DisplayErrorMessage("WiFiAPSaveMessage", this.responseText);
            }   
        }        
    }),
    
    /* Save HTTP login and pass settings */
    btnSaveHttpSet.addEventListener("click", function (){
        
        if(CheckPageSettings() == false) 
        {   
            clearTimeout(TOPageConf);
            btnSaveHttpSet.innerHTML = langHtmlMult.btnNameHTMLSave[EVSE.language];
            btnSaveHttpSet.style.backgroundColor = "#3071A9";

            if( statePageConf == Started)
            {
                statePageConf = Finished;
                this.innerHTML = langHtmlMult.btnNameHTMLSave[EVSE.language];
                this.style.backgroundColor = "#3071A9";
            }
            return;
        }

        if(statePageConf == Finished)
        {        
            statePageConf = Started;
            DisplayErrorMessage("HTMLSaveMessage", msg.wifiConfirm, 'Green');
            this.innerHTML = langHtmlMult.btnNameHTMLConf[EVSE.language];
            this.style.backgroundColor = "Green";

            clearTimeout(TOPageConf);

            TOPageConf = setTimeout(function () {
                statePageConf = Finished;
                btnSaveHttpSet.innerHTML = langHtmlMult.btnNameHTMLSave[EVSE.language];
                btnSaveHttpSet.style.backgroundColor = "#3071A9";
                DisplayErrorMessage("HTMLSaveMessage", "");
            }, 10000);
            return;
        }

        if(statePageConf == InProgess) 
        {
            return;
        }

        statePageConf = InProgess;
        
        DisplayErrorMessage("HTMLSaveMessage", msg.wifiConfirmAfter, 'Green');
        
        this.innerHTML = langHtmlMult.btnNameHTMLSave[EVSE.language];
        this.style.backgroundColor = "#3071A9";
       
        clearTimeout(TOPageConf);
        setTimeout(function () {
            statePageConf = Finished;
            DisplayErrorMessage("HTMLSaveMessage", "");
        }, 10000);

        let req = new XMLHttpRequest();
        req.open("POST", "/configHttp", true),
        req.setRequestHeader("Content-type", "application/x-www-form-urlencoded"),
        req.send(
            "httpUsername=" + encodeURIComponent(EVSE.httpUsername) +
            "&httpPassword=" + encodeURIComponent(EVSE.httpPassword) +
            "&httpPasswordConf=" + encodeURIComponent(EVSE.httpPasswordConf)
        ),
        req.onreadystatechange = function() {
            if ((req.readyState == 4) && (req.status == 200)) {
                if(this.responseText.length > 0)
                    DisplayErrorMessage("HTMLSaveMessage",  this.responseText, 'Red');
            }   
        }
    }),

    /* Old save settings */
    btnSaveNetSet.addEventListener("click", function () {

        if(CheckSTASettings() == false) 
        {   
            clearTimeout(TOStaConf);
            btnSaveNetSet.innerHTML = langHtmlMult.btnNameWifiSTAConf[EVSE.language];
            btnSaveNetSet.style.backgroundColor = "#3071A9";

            if(stateStaConf == Started)
            {
                stateStaConf = Finished;
                this.innerHTML = langHtmlMult.btnNameWifiSTASave[EVSE.language];
                this.style.backgroundColor = "#3071A9";
            }

            return;
        }

        if(stateStaConf == Finished)
        {        
            stateStaConf = Started;
            DisplayErrorMessage("WiFiSTASaveMessage", msg.wifiConfirm, 'Green');           
            this.innerHTML = langHtmlMult.btnNameWifiSTAConf[EVSE.language];
            this.style.backgroundColor = "Green";
            
            clearTimeout(TOStaConf);
            TOStaConf = setTimeout(function () {
                statePageConf = Finished;
                btnSaveNetSet.innerHTML = langHtmlMult.btnNameWifiSTAConf[EVSE.language];
                btnSaveNetSet.style.backgroundColor = "#3071A9";
                DisplayErrorMessage("WiFiSTASaveMessage", "");
            }, 10000);
            return;
        }

        if(stateStaConf == InProgess) 
        {
            return;
        }

        stateStaConf = InProgess;
        DisplayErrorMessage("WiFiSTASaveMessage", msg.wifiConfirmAfter, 'Green');
        this.innerHTML = langHtmlMult.btnNameWifiSTASave[EVSE.language];
        this.style.backgroundColor = "#3071A9";

        clearTimeout(TOStaConf);
        setTimeout(function () {
            stateStaConf = Finished;
            DisplayErrorMessage("WiFiSTASaveMessage", "");
        }, 10000);
         
        let e = new XMLHttpRequest();
        e.open("POST", "/config", true),
        e.setRequestHeader("Content-type", "application/x-www-form-urlencoded"),
        e.send(
            "ssidName=" + 
            encodeURIComponent(EVSE.ssidName) +
            "&ssidPassword=" + 
            encodeURIComponent(EVSE.ssidPassword) +
            "&ssidPasswordConf=" + 
            encodeURIComponent(EVSE.ssidPasswordConf) +
            "&WifiMode=" + 
            EVSE.WifiMode +
            "&mac_bind=" + 
            EVSE.mac_bind +
            "&STA_MAC=" +
            EVSE.STA_MAC
        ),
        e.onreadystatechange = function() {
            if ((e.readyState == 4) && (e.status == 200)) {
                if(this.responseText.length > 0)
                    DisplayErrorMessage("WiFiSTASaveMessage", this.responseText, 'Red');
            }   
        }

        
    });

    
    // ocppVendor.addEventListener("change", () => {
    //     const selectedValue = ocppVendor.value;
    
    //    if (selectedValue == "0") {
    //        linkToApp.style.display = "none";
    //        showModal("Offline");
    //    EVSE.ocppVendor = 0;
    //    } else if (selectedValue == "255") {
    //        linkToApp.style.display = "none"; 
    //        showModal("Custom");
    //        EVSE.ocppVendor = 255;
    //    } else {
    //        linkToApp.style.display = "block"; 
    
    //        if (selectedValue == "1") {
    //            linkToApp.href = "https://grizzl-e.com/connect/";
    //            showModal("Connect");
    //            EVSE.ocppVendor = 1;
    //        } 
    //        else if (selectedValue == "2") {
    //            linkToApp.href = "https://epiccharging.com/mobileapp";
    //            showModal("EpicCharging");
    //            EVSE.ocppVendor = 2;
    //        }
    //        else if (selectedValue == "3") {
    //            linkToApp.href = "https://www.ev.energy/en-us/drivers";
    //            showModal("EVEnergy");
    //            EVSE.ocppVendor = 3;
    //        }
    //        else if (selectedValue == "4")
    //        {
    //            linkToApp.href = "https://chargelab.co/app";
    //            showModal("ChargeLab");
    //            EVSE.ocppVendor = 4; 
    //        }
    //        else if (selectedValue == "5")
    //        {
    //            linkToApp.href = "https://swtchenergy.com/drivers";
    //            showModal("SWTCH");
    //            EVSE.ocppVendor = 5; 
    //        }

    //    }
    //});
    
  //  popupSave.addEventListener('click', () => {
  //      if (EVSE.ocppVendor === 255) {
            // Redirect to /ocppconfig for the Custom option
  //          window.open("/ocppconfig", "_blank");
  //      } else {
            // Process the changes for other options
  //          postPageEvent("ocppVendor", parseInt(EVSE.ocppVendor));
  //      }
  //      lastSelectedIndex = ocppVendor.value;
  //      hideModal();
  //  });
    // popupSave.addEventListener('click', () => {
    //    postPageEvent("ocppVendor", parseInt(EVSE.ocppVendor));
    //    lastSelectedIndex = ocppVendor.value;
    //    hideModal();
 
    //    if (EVSE.ocppVendor === 255) {
    //        // Redirect to /ocppconfig for the Custom option
         //   window.open("/ocppconfig", "_blank");
    //        document.location.href="/ocppconfig";
    //    }
    // });
    
    // popupCancel.addEventListener("click", () => {
        // Revert to the last selected index
    //      ocppVendor.value = lastSelectedIndex;
        // lastSelectedIndex = ocppVendor.value;
        // lastSelectedIndexCancel = ocppVendor.value;
    //      hideModal();
    // });
    
    // cmodalOverlay.addEventListener("click", () => {
        // Simply close the modal without reverting the selection
        // lastSelectedIndex = ocppVendor.value;
    //    ocppVendor.value = lastSelectedIndex;
        // console.log(lastSelectedIndex);
    //    hideModal();
    // });

    
    function showModal(descriptionKey) {
        const language = languageValue.value;
        const description =
            descriptions[descriptionKey]?.[language] || descriptions[descriptionKey]?.["EN"]; // Fallback to English
    
        const descriptionElement = document.querySelector("#popupModal .description");
        descriptionElement.innerHTML = description;
    
        descriptionElement.className = "description";
        if (language === "UA") {
            descriptionElement.classList.add("ua");
        }
        if (language === "FR") {
            descriptionElement.classList.add("fr");
        }
        if (language === "SP") {
            descriptionElement.classList.add("sp");
        }
    
        modalOverlay.style.display = "block";
        popupModal.style.display = "block";
    
        setTimeout(() => {
            modalOverlay.style.opacity = "1";
            popupModal.style.opacity = "1";
            popupModal.style.transform = "translate(-50%, -50%) scale(1)";
        }, 10);
    }
    
    function hideModal() {
        modalOverlay.style.opacity = "0";
        popupModal.style.opacity = "0";
        popupModal.style.transform = "translate(-50%, -50%) scale(0)";
        setTimeout(() => {
            modalOverlay.style.display = "none";
            popupModal.style.display = "none";
        }, 300);
    }
    



    /* Timer type switch handler */
    timerTypeValue.addEventListener("input", function () {
        switch (timerTypeValue.value){
            case "noPWM":
                postPageEvent("timerType", 0);
                break;
            case "VAG":
                postPageEvent("timerType", 1);
                break;
        }
    });

    /* Language  switch handler */
    languageValue.addEventListener("input", function () {
        EVSE.language = langList.indexOf(languageValue.value);
        changeLang(EVSE.language);
        postPageEvent("lang", EVSE.language);
    });

    /* MinVoltage switch handler */
    minVoltageValue.addEventListener("input", function () {
        rangeSliderAIVoltage.min =  minVoltageValue.value + 10;
        postPageEvent("minVoltage", parseInt(minVoltageValue.value));
    });

    /* Suspend limits */
    switchSuspendLimits.addEventListener("input", function () {
        if(switchSuspendLimits.checked){
            EVSE.suspendLimits = 1;
            switchTimeLimit.checked     = 0;
            switchEnergyLimit.checked   = 0;
            switchMoneyLimit.checked    = 0;
            EVSE.energyLimit = 0;
            energyLimitValue.textContent = (EVSE.energyLimit).toFixed(3); 
            rangeSliderEnergyLimit.value = (EVSE.energyLimit * 10).toFixed(0);

            EVSE.timeLimit = 0;
            timeLimitValue.textContent = secondsToStr(EVSE.timeLimit); 
            rangeSliderTimeLimit.value = EVSE.timeLimit;

            EVSE.moneyLimit = 0;
            moneyLimitValue.textContent = (EVSE.moneyLimit).toFixed(2); 
            rangeSliderMoneyLimit.value = (EVSE.moneyLimit * 10).toFixed(0);


        }else{
            EVSE.suspendLimits = 0;  
        }
        postPageEvent("suspendLimits", EVSE.suspendLimits);
    });
    
    /* Time limit switch handler */
    switchTimeLimit.addEventListener("input", function () {
        if(switchTimeLimit.checked){
            EVSE.timeLimitS = 1;
        }else{
            EVSE.timeLimitS = 0;
        }
        postPageEvent("timeLimitS", EVSE.timeLimitS);
    });

    /* Time limit slider handler */
    rangeSliderTimeLimit.addEventListener("input", function () {
        timeLimitValue.textContent = secondsToStr(rangeSliderTimeLimit.value); 
        EVSE.timeLimit = rangeSliderTimeLimit.value; 
        
        Debounce.timeLimit.txData(EVSE.timeLimit);
    });

    /* Energy limit switch handler */
    switchEnergyLimit.addEventListener("input", function () {
        if(switchEnergyLimit.checked){
            EVSE.energyLimitS = 1;
        }else{
            EVSE.energyLimitS = 0;
        }

        postPageEvent("energyLimitS", EVSE.energyLimitS); 
    });

    /* Energy limit slider handler */
    rangeSliderEnergyLimit.addEventListener("input", function () {
        EVSE.energyLimit = (rangeSliderEnergyLimit.value/10); 
        energyLimitValue.textContent = (EVSE.energyLimit).toFixed(3);       
        Debounce.energyLimit.txData(EVSE.energyLimit * 10);
    });

    /* Money limit switch handler */
    switchMoneyLimit.addEventListener("input", function () {
        if(switchMoneyLimit.checked){
            EVSE.moneyLimitS = 1;
        }else{
            EVSE.moneyLimitS = 0;
        }
        postPageEvent("moneyLimitS", EVSE.moneyLimitS); 
    });

    /* Money limit slider handler */
    rangeSliderMoneyLimit.addEventListener("input", function () {
        EVSE.moneyLimit = (rangeSliderMoneyLimit.value / 10); 
        moneyLimitValue.textContent = (EVSE.moneyLimit).toFixed(2); 

        Debounce.moneyLimit.txData(EVSE.moneyLimit);

    });

    btnSaveRates.addEventListener("click", function () {
        
        postPageEvent("tarif",  EVSE.tarif_1);
        postPageEvent("tarifAValue",  EVSE.tarifAValue);
        postPageEvent("tarifBValue",  EVSE.tarifBValue);
        postPageEvent("tarifAStart", EVSE.tarifAStart);
        postPageEvent("tarifAStop", EVSE.tarifAStop);
        postPageEvent("tarifBStart", EVSE.tarifBStart);
        postPageEvent("tarifBStop", EVSE.tarifBStop);
        setTimeout(function () {
            allowDataSending = true;
        }, 2000);
    });

    tarif_1.addEventListener("focus", function () {
        allowDataSending = false;
        postPageEvent("tarifClicked", 1);
    });
    tarifAValue.addEventListener("focus", function (){
        allowDataSending = false;
        postPageEvent("tarifAClicked", 1);
    });
    tarifBValue.addEventListener("focus", function (){
        allowDataSending = false;
        postPageEvent("tarifBClicked", 1);
    });
    
    
    /* Tarif 1 input handler */
    tarif_1.addEventListener("blur", function (){
        //if (this.value.length > 7) this.value = this.value.substr(0, 7);
        if (this.valueAsNumber < this.min) this.value =  this.min;
        if (this.valueAsNumber > this.max) this.value = this.max; 
        EVSE.tarif_1 = tarif_1.valueAsNumber * 100;
        // postPageEvent("tarif", EVSE.tarif_1);
        allowDataSending = false;
    });
    

    /* Tarif A input handler */
    tarifAValue.addEventListener("blur", function (){
        if (this.valueAsNumber < this.min) this.value =  this.min;
        if (this.valueAsNumber > this.max) this.value = this.max; 
        EVSE.tarifAValue = tarifAValue.valueAsNumber * 100;
        
        allowDataSending = false;
    });

    /* Tarif A control switch */
    tarifAEnable.addEventListener("input", function () {
        (tarifAEnable.checked) ? EVSE.tarifAEnable = 1 : EVSE.tarifAEnable = 0;
        postPageEvent("tarifAEnable", EVSE.tarifAEnable);
    });

    /* Tarif A start */
    tarifAStart.addEventListener("blur", function () {
        EVSE.tarifAStart = stringToMinutes(tarifAStart.value);
        allowDataSending = false;
    });

    /* Tarif A stop */
    tarifAStop.addEventListener("input", function () {
        EVSE.tarifAStop = stringToMinutes(tarifAStop.value);
        allowDataSending = false;
    });

    /* Tarif B input handler */
    tarifBValue.addEventListener("blur", function (){
        if (this.valueAsNumber < this.min) this.value =  this.min;
        if (this.valueAsNumber > this.max) this.value = this.max; 
        EVSE.tarifBValue = tarifBValue.valueAsNumber * 100;
        allowDataSending = false;
    });

    /* Tarif B control switch */
    tarifBEnable.addEventListener("input", function () {
        (tarifBEnable.checked) ? EVSE.tarifBEnable = 1 : EVSE.tarifBEnable = 0;
        postPageEvent("tarifBEnable", EVSE.tarifBEnable);
    });

    /* Tarif B start */
    tarifBStart.addEventListener("input", function () {
        EVSE.tarifBStart = stringToMinutes(tarifBStart.value);
        allowDataSending = false;
    });

    /* Tarif B stop */
    tarifBStop.addEventListener("input", function () {
        EVSE.tarifBStop = stringToMinutes(tarifBStop.value);
        allowDataSending = false;
    });



    /* One charge control switch */
    switchOneCharge.addEventListener("input", function () {
        (switchOneCharge.checked) ? EVSE.oneCharge = 1 : EVSE.oneCharge = 0;
        postPageEvent("oneCharge", EVSE.oneCharge);
    });


    /* Schedule 1 switch */
    switchSchedule1.addEventListener("input", function (){
        if(switchSchedule1.checked){
            EVSE.sh1Enabled = 1
        }else{
            EVSE.sh1Enabled = 0;
        }
        postPageEvent("sh1Enabled", EVSE.sh1Enabled);
    });

    startSchedule1.addEventListener("focus", function () {
        allowDataSending = false;
    });   
    stopSchedule1.addEventListener("focus", function () {
        allowDataSending = false;
    });
    /* Schedule 1 start */
    startSchedule1.addEventListener("blur", function () {
        EVSE.sh1Start = stringToMinutes(startSchedule1.value);
        postPageEvent("sh1Start", EVSE.sh1Start);
        allowDataSending = false;
    });
    
    /* Schedule 1 stop */
    stopSchedule1.addEventListener("blur", function () {
        EVSE.sh1Stop = stringToMinutes(stopSchedule1.value);
        postPageEvent("sh1Stop", EVSE.sh1Stop);
        allowDataSending = false;
        setTimeout(function () {
            allowDataSending = true;
        }, 2000);
    });
    
    /* Schedule 1 current switch*/
    sch1_switch_current.addEventListener("input", function () {
        if(sch1_switch_current.checked){
            EVSE.sh1CurrentEnable = 1;            
        }else{
            EVSE.sh1CurrentEnable = 0;   
        }
        postPageEvent("sh1CurrentEnable", EVSE.sh1CurrentEnable);
    });
    
    /* Schedule 1 current slider*/
    sch1_range_slider_current.addEventListener("input", function() {
        EVSE.sh1CurrentValue = sch1_range_slider_current.value;
        sch1_current_limit_value.textContent =  EVSE.sh1CurrentValue;
        // postPageEvent("sh1CurrentValue", EVSE.sh1CurrentValue);
        Debounce.sh1CurrentValue.txData(EVSE.sh1CurrentValue);
    });

    /* Schedule 1 energy switch*/
    sch1_switch_energy.addEventListener("input", function () {
        if(sch1_switch_energy.checked){
            EVSE.sh1EnergyEnable = 1;
        }else{
            EVSE.sh1EnergyEnable = 0;            
        }
        postPageEvent("sh1EnergyEnable", EVSE.sh1EnergyEnable);
    });
        
    /* Schedule 1 energy slider*/
    sch1_range_slider_energy.addEventListener("input", function() {
        EVSE.sh1EnergyValue = (sch1_range_slider_energy.value / 10);
        sch1_energy_limit_value.textContent =  (EVSE.sh1EnergyValue).toFixed(3);
        //postPageEvent("sh1EnergyValue", EVSE.sh1EnergyValue);
        Debounce.sh1EnergyValue.txData(EVSE.sh1EnergyValue * 10);
    });      

    /* Schedule 2 switch */
    switchSchedule2.addEventListener("input", function () {
        if(switchSchedule2.checked){
            EVSE.sh2Enabled = 1
        }else{
            EVSE.sh2Enabled = 0;
        }
        postPageEvent("sh2Enabled", EVSE.sh2Enabled);
    });

    startSchedule2.addEventListener("focus", function () {
        allowDataSending = false;
    });

    stopSchedule2.addEventListener("focus", function () {
        allowDataSending = false;
    });
    
    /* Schedule 2 start */
    startSchedule2.addEventListener("blur", function () {
        EVSE.sh2Start = stringToMinutes(startSchedule2.value);    
        postPageEvent("sh2Start", EVSE.sh2Start);
        allowDataSending = false;
    });
    
    /* Schedule 2 stop */
    stopSchedule2.addEventListener("blur", function () {
        EVSE.sh2Stop = stringToMinutes(stopSchedule2.value);
        postPageEvent("sh2Stop", EVSE.sh2Stop);
        allowDataSending = false;
        setTimeout(function () {
            allowDataSending = true;
        }, 2000);
    });
    
    /* Schedule 2 current switch*/
    sch2_switch_current.addEventListener("input", function () {
        if(sch2_switch_current.checked){
            EVSE.sh2CurrentEnable = 1;
        }else{
            EVSE.sh2CurrentEnable = 0;
        }
        postPageEvent("sh2CurrentEnable", EVSE.sh2CurrentEnable);
    });

    /* Schedule 2 current slider*/
    sch2_range_slider_current.addEventListener("input", function() {
        EVSE.sh2CurrentValue = sch2_range_slider_current.value;
        sch2_current_limit_value.textContent =  EVSE.sh2CurrentValue;
        //postPageEvent("sh2CurrentValue", EVSE.sh2CurrentValue);
        Debounce.sh2CurrentValue.txData(EVSE.sh2CurrentValue);
    });

    /* Schedule 2 energy switch*/
    sch2_switch_energy.addEventListener("input", function () {
        if(sch2_switch_energy.checked){
            EVSE.sh2EnergyEnable = 1;
        }else{
            EVSE.sh2EnergyEnable = 0;
        }
        postPageEvent("sh2EnergyEnable", EVSE.sh2EnergyEnable);
    });
        
    /* Schedule 2 energy slider*/
    sch2_range_slider_energy.addEventListener("input", function() {
        EVSE.sh2EnergyValue = (sch2_range_slider_energy.value / 10);
        sch2_energy_limit_value.textContent =  (EVSE.sh2EnergyValue).toFixed(3);
        //postPageEvent("sh2EnergyValue", EVSE.sh2EnergyValue);
        Debounce.sh2EnergyValue.txData(EVSE.sh2EnergyValue * 10);
    });      


    /* Charge now */
    chargeNow.addEventListener("click", function() {

        switchSuspendLimits.checked = 0;
        switchOneCharge.checked     = 0;
        switchTimeLimit.checked     = 0;
        switchEnergyLimit.checked   = 0;
        switchMoneyLimit.checked    = 0;
        switchEvseEnabled.checked   = 0;
        switchSchedule1.checked     = 0; 
        switchSchedule2.checked     = 0;
        
        sch1_switch_current.checked = 0; 
        sch2_switch_current.checked = 0; 
        sch1_switch_energy.checked  = 0; 
        sch2_switch_energy.checked  = 0; 
        
        postPageEvent("chargeNow", EVSE.limitsStatus);
    });

    /* Independed energy meters reset */
    btnResetIEM1.addEventListener("click", function () {
        if(counterAResetConf == Finished)
        {
            clearInterval(TOAResetConf);

            TOAResetConf = setTimeout(function(){
                btnResetIEM1.innerHTML = langHtmlMult.btnNameResetIEMeterA[EVSE.language];
                btnResetIEM1.style.backgroundColor = "#3071A9";
                counterAResetConf = Finished;
                DisplayErrorMessage("CounterAMessage", "");
            }, 10000);

            counterAResetConf = Started;
            DisplayErrorMessage("CounterAMessage", msg.confirmResetIEM1, 'green');
            this.innerHTML = langHtmlMult.btnNameResetConf[EVSE.language];
            this.style.backgroundColor = "green";
            return;
        }

        if(counterAResetConf == InProgess)
            return;

        if(counterAResetConf == Started)
            counterAResetConf = InProgess;
    
        DisplayErrorMessage("CounterAMessage", msg.confirmResetIEM1After, 'green');
        this.innerHTML = langHtmlMult.btnNameResetIEMeterA[EVSE.language];
        this.style.backgroundColor = "#3071A9";

        clearInterval(TOAResetConf);
        setTimeout(function(){
            counterAResetConf = Finished;
            DisplayErrorMessage("CounterAMessage", "");
        }, 10000);
        
        postPageEvent("rstEM1");     
    });

    btnResetIEM2.addEventListener("click", function () {
        if(counterBResetConf == Finished){
            clearInterval(TOBResetConf);
            TOBResetConf = setTimeout(function(){
                btnResetIEM2.innerHTML = langHtmlMult.btnNameResetIEMeterB[EVSE.language];
                btnResetIEM2.style.backgroundColor = "#3071A9";
                counterBResetConf = Finished;
                DisplayErrorMessage("CounterBMessage", "");
            }, 10000);

            counterBResetConf = Started;
            DisplayErrorMessage("CounterBMessage", msg.confirmResetIEM2, 'green');
            this.innerHTML = langHtmlMult.btnNameResetConf[EVSE.language];
            this.style.backgroundColor = "green";
            return;
        }

        if(counterBResetConf == InProgess)
            return;

        if(counterBResetConf == Started)
            counterBResetConf = InProgess;
    
        DisplayErrorMessage("CounterBMessage", msg.confirmResetIEM2After, 'green');
        this.innerHTML = langHtmlMult.btnNameResetIEMeterB[EVSE.language];
        this.style.backgroundColor = "#3071A9";

        clearInterval(TOBResetConf);
        setTimeout(function(){
            counterBResetConf = Finished;
            DisplayErrorMessage("CounterBMessage", "");
        }, 10000);

        postPageEvent("rstEM2");     
    });

    /* Get time button handler */
    btnGetTime.addEventListener("click",(function() {
        let userDate = new Date;
        EVSE.systemTime = parseInt((userDate / 1000).toFixed(0));
        postPageEvent("systemTime",  EVSE.systemTime);
    }));

    /* Get timeZone button handler */
    timeZoneValue.addEventListener("input",(function(){
        if(timeZoneValue.value < -12){timeZoneValue.value = -12;}
        if(timeZoneValue.value > 12){timeZoneValue.value = 12;}
        if(false == isNaN(parseInt(timeZoneValue.value))) {
            EVSE.timeZone = parseInt(timeZoneValue.value);
            postPageEvent("timeZone",  EVSE.timeZone);
        }
    }));
    
    /* Factory reset */
    btnFactoryReset.addEventListener("click", function () {
        if(factoryResetConf == Finished) {
            clearInterval(TOFResetConf);
            TOFResetConf = setTimeout(function(){
                btnFactoryReset.innerHTML = "Reset";
                btnFactoryReset.style.backgroundColor = "#3071A9";
                factoryResetConf = Finished;
                DisplayErrorMessage("FactoryResetMessage", "");
            }, 10000);

            factoryResetConf = Started;
            DisplayErrorMessage("FactoryResetMessage", msg.confirmFactoryReset, 'green');
            this.innerHTML = langHtmlMult.btnNameResetConf[EVSE.language];
            this.style.backgroundColor = "green";
            return;
        }

        if(factoryResetConf == InProgess)
            return;

        if(factoryResetConf == Started)
            factoryResetConf = InProgess;
    
        DisplayErrorMessage("FactoryResetMessage", msg.confirmFactoryResetAfter, 'green');
        this.innerHTML = "Reset";
        this.style.backgroundColor = "#3071A9";

        clearInterval(TOFResetConf);
        setTimeout(function(){
            factoryResetConf = Finished;
            DisplayErrorMessage("FactoryResetMessage", "");
        }, 10000);
        
        postPageEvent("factoryReset");      
    });

    //    btnFwUpdate.addEventListener("click", function () {
    //    document.location.href="/autoupdate";
    // });

    btnOCPPConfig.addEventListener("click", function () {
        document.location.href="/ocppconfig";
    });

}); /* DOM loaded */


/*-----------------------------------------------------------------------------------------*/
/*                          Requeset "/Init"  onLoad <Body>                                */
/*               Inits wifi settings, min, max currents and limits state                   */
/*-----------------------------------------------------------------------------------------*/ 
function getDataInit() 
{
    let dataInit;
    let request1 = new XMLHttpRequest();
    request1.open("POST", "/init", true);
    request1.send();
    request1.onreadystatechange = function() {
        if ((request1.readyState == 4) && (request1.status == 200)) {
            dataInit = JSON.parse(this.responseText);
            
          
            /* Lang type  */

            if (dataInit.hasOwnProperty("lang")) {
                if(EVSE.language != dataInit.lang) {
                    EVSE.language = dataInit.lang;
                    languageValue.value = langList[EVSE.language];
                    changeLang(EVSE.language);
                }
            }


            /* Design current */
            if (dataInit.hasOwnProperty("curDesign")){
                if(EVSE.evseDesignCurrent != dataInit.curDesign)
                {
                    EVSE.evseDesignCurrent = dataInit.curDesign;
                    rangeSliderCurrent.max = EVSE.evseDesignCurrent;
                    sch1_range_slider_current.max = EVSE.evseDesignCurrent;
                    sch2_range_slider_current.max = EVSE.evseDesignCurrent;
                }
            }

            
            /*  Min current */
            if (dataInit.hasOwnProperty("minCurrent")){
                EVSE.evseMinCurrent = dataInit.minCurrent;
                rangeSliderCurrent.min = EVSE.evseMinCurrent;
                sch1_range_slider_current.min = EVSE.evseMinCurrent;
                sch2_range_slider_current.min = EVSE.evseMinCurrent;
            }
            
            /*  Wifi mode */
            if (dataInit.hasOwnProperty("WifiMode")){
                if(dataInit.WifiMode == 2){
                    EVSE.WifiMode = dataInit.WifiMode;
                    switchWifiMode.checked = false;
                }else if(dataInit.WifiMode == 3){
                    EVSE.WifiMode = dataInit.WifiMode;
                    switchWifiMode.checked = true;
                } else {
                    EVSE.WifiMode = 2; // AP
                    switchWifiMode.checked = false;
                }
            }
            if (dataInit.hasOwnProperty("broadcastMode")){
                if(dataInit.broadcastMode == 1){ // STA
                    EVSE.broadcastMode = dataInit.broadcastMode;
                    switchBroadcastMode.checked = false;
                } else if (dataInit.broadcastMode == 0){
                    EVSE.broadcastMode = dataInit.broadcastMode;
                    switchBroadcastMode.checked = true;
                }
            }

            /*  bind MAC */
            if (dataInit.hasOwnProperty("mac_bind")){
                EVSE.mac_bind = dataInit.mac_bind;
                if(EVSE.mac_bind == 1){
                    switch_mac_bind.checked = true;
                }else{
                    switch_mac_bind.checked = false;
                } 
            }

            /*  STA MAC address */
            if (dataInit.hasOwnProperty("STA_MAC")){
                EVSE.STA_MAC = dataInit.STA_MAC;
                STA_MAC_value.value = EVSE.STA_MAC;
            }
         
            /*  ESP MAC address */
            if (dataInit.hasOwnProperty("ESP_MAC")){
                EVSE.ESP_MAC = dataInit.ESP_MAC;
                ESP_MACValue.value = EVSE.ESP_MAC;
            }
            
            /*  HTTP settings */
            if (dataInit.hasOwnProperty("httpUsername") && dataInit.hasOwnProperty("httpPassword")){
                httpName.value = EVSE.httpUsername = decodeURIComponent(dataInit.httpUsername);
                httpPassword.value = EVSE.httpPassword = decodeURIComponent(dataInit.httpPassword);
                httpPasswordConf.value = EVSE.httpPasswordConf = decodeURIComponent(dataInit.httpPassword);
            }
            
            /*  AP settings */
            if (dataInit.hasOwnProperty("ssidNameAP") && dataInit.hasOwnProperty("ssidPasswordAP")){
                nameAP.value = EVSE.ssidNameAP = decodeURIComponent(dataInit.ssidNameAP);
                passwordAP.value = EVSE.ssidPasswordAP = decodeURIComponent(dataInit.ssidPasswordAP);
                passwordAPConf.value = EVSE.ssidPasswordAPConf = decodeURIComponent(dataInit.ssidPasswordAP);
            }
            
            /*  STA settings */
            if (dataInit.hasOwnProperty("ssidName") && dataInit.hasOwnProperty("ssidPassword")){
                netName.value = EVSE.ssidName = decodeURIComponent(dataInit.ssidName);
                netPassword.value = EVSE.ssidPassword = decodeURIComponent(dataInit.ssidPassword);
            }           
        
            /* Once update time */
            let userDate = new Date;
            EVSE.systemTime = parseInt((userDate / 1000).toFixed(0));
            postPageEvent("systemTime",  EVSE.systemTime);
        }
    };
} /* getDataInit() */


/*-----------------------------------------------------------------------------------------*/
/*                          Main loop()  postDataMain                                      */
/*                          every second post data to server                               */
/*-----------------------------------------------------------------------------------------*/ 

var requests = [];
let countNoConnection = 0;

function postDataMain() {     
    let dataMain = {};
    let requestMain = new XMLHttpRequest();
    requestMain.open("POST", "/main", true);
    requestMain.timeout = 1000; // 1Sec
    requestMain.send();
    requests.push(requestMain); // Add processing request to the list
    
    requestMain.onerror = function() {
        HandleConnectionLost();
    }
    requestMain.ontimeout = function() {
        console.log("ontimeout");
        requestMain.abort();
        HandleConnectionLost();
    }
    requestMain.onreadystatechange = function() {
        if (requestMain.readyState == 4 && requestMain.status != 200) { 
            HandleConnectionLost();
        }
        if (requestMain.readyState == 4 && requestMain.status == 200) {
            remove(requests, requestMain); 
            HandleConnectionRecovery();
            dataMain = JSON.parse(requestMain.responseText);
            /*------------------------------- Test recived data ---------------------------------------*/
            if (testValid(dataMain)) {
                
                /*------------------------------- Init data at first run-----------------------------------*/
                if (needInit) {
                    needInit = 0;                 

                    /* MinVoltage value  */
                    if (dataMain.hasOwnProperty("minVoltage")){
                        minVoltageValue.value = dataMain.minVoltage + "";
                        rangeSliderAIVoltage.min =  dataMain.minVoltage + 10;
                    }

                    /* Lang type  */
                    if (dataMain.hasOwnProperty("lang")) {
                        if(EVSE.language != dataMain.lang) {
                            EVSE.language = dataMain.lang;
                            languageValue.value = langList[EVSE.language];
                            changeLang(EVSE.language);
                        }
                    }
                    // if (dataMain.hasOwnProperty("switchState")) {
                    //     if(EVSE.switchState != dataMain.switchState) {
                    //         EVSE.switchState = dataMain.switchState;
                    //     }
                    // }

                    if (dataMain.hasOwnProperty("switchState")) {
                        console.log('Switch State: 0x' + dataMain.switchState.toString(16).toUpperCase());
                    }
                    
                    // if (dataMain.hasOwnProperty("ocppVendor")) {
                    //    if(EVSE.ocppVendor != dataMain.ocppVendor) {
                    //        EVSE.ocppVendor = dataMain.ocppVendor;
                    //        ocppVendor.value = EVSE.ocppVendor;
                    //        lastSelectedIndex = ocppVendor.value;
                    //    }
                    // }


                    /* Sta IP */
                    if (dataMain.hasOwnProperty('STA_IP_Addres')) {
                        EVSE.localIP = dataMain.STA_IP_Addres;
                        localIpValue.value =  EVSE.localIP;
                    }

                    /* Design current */
                    if (dataMain.hasOwnProperty("curDesign")){
                        // if(EVSE.evseDesignCurrent != dataMain.curDesign)
                        // {
                        EVSE.evseDesignCurrent = dataMain.curDesign;
                        rangeSliderCurrent.max = EVSE.evseDesignCurrent;
                        sch1_range_slider_current.max = EVSE.evseDesignCurrent;
                        sch2_range_slider_current.max = EVSE.evseDesignCurrent;
                        console.log(dataMain.curDesign);
                        // }
                    }

                    if (dataMain.hasOwnProperty("broadcastMode")){
                        if(EVSE.broadcastMode != dataMain.broadcastMode)
                        {
                            EVSE.broadcastMode = dataMain.broadcastMode;
                            if (dataMain.broadcastMode == 1)
                            {
                                switchBroadcastMode.checked = false;
                            }
                            else if (dataMain.broadcastMode == 0)
                            {
                                switchBroadcastMode.checked = true;
                            }
                            else{
                                EVSE.broadcastMode = 0; // AP
                                switchBroadcastMode.checked = true;
                            }
                        }
                    }
                    
                    /*  Min current */
                    if (dataMain.hasOwnProperty("minCurrent")){
                        if(EVSE.evseMinCurrent != dataMain.minCurrent)
                        {
                            EVSE.evseMinCurrent = dataMain.minCurrent;
                            rangeSliderCurrent.min = EVSE.evseMinCurrent;
                            sch1_range_slider_current.min = EVSE.evseMinCurrent;
                            sch2_range_slider_current.min = EVSE.evseMinCurrent;
                        }
                    }
                   
                    // /* Adapter  */
                    // if (dataMain.hasOwnProperty('adapter')) {
                    //     EVSE.adapter = dataMain.adapter;
                    //     if (EVSE.adapter <= 12 ) {
                    //         rangeSliderCurrent.max = 12;
                    //         sch1_range_slider_current.max = 12;
                    //         sch2_range_slider_current.max = 12;
                    //     } 
                    //     else if(EVSE.adapter != 255)
                    //     {
                    //         rangeSliderCurrent.max = EVSE.evseDesignCurrent;
                    //         sch1_range_slider_current.max = EVSE.evseDesignCurrent;
                    //         sch2_range_slider_current.max = EVSE.evseDesignCurrent;
                    //     }
                    // }



                    /* Current set */
                    if (dataMain.hasOwnProperty('currentSet')) 
                    {
                        
                        if(Debounce.currentSet.ignoreFlag == 0)
                        {                      
                            EVSE.currentSet = dataMain.currentSet;
                            // if ((EVSE.currentSet > 12) && (EVSE.gridRange == 1)) {
                            //     EVSE.currentSet = 12;
                            postPageEvent("currentSet", EVSE.currentSet);
                            // }
                            rangeSliderCurrent.value = EVSE.currentSet;
                        }
                    }
                    

                    /* Adaptation switch status */
                    if (switchAIMode.checked == true) 
                    {
                        AIModeSelect.disabled = false;
                        //currentLimitValue.textContent = EVSE.aiModeCurrent + " /" + EVSE.currentSet;
                        for(var i = 0; i < currentLimitValue.length; i++)
                        { 
                            currentLimitValue[i].textContent = EVSE.aiModeCurrent + " /" + EVSE.currentSet;
                        }

                    } 
                    else 
                    {
                        AIModeSelect.disabled = true;
                        //currentLimitValue.textContent = EVSE.currentSet;

                        for(var i = 0; i < currentLimitValue.length; i++)
                        { 
                            currentLimitValue[i].textContent = EVSE.currentSet;
                        }
                    }

                    /* Adaptation mode status */
                    if (dataMain.hasOwnProperty('aiStatus')) {
                        
                        EVSE.aiMode = dataMain.aiStatus;

                        if(dataMain.aiStatus == 1) 
                        {
                            AIModeSelect.value = "AI_MODE_1";
                            switchAIMode.checked = true;
                            AIModeSelect.disabled = false;
                            //rangeSliderAIVoltage.disabled = false;
                            AIVoltageBlock.hidden = false;
                            AIAutoBlock.hidden = true;
                            AIPowerBlock.hidden = true; 
                        }
                        else if (dataMain.aiStatus == 2) 
                        {
                            AIModeSelect.value = "AI_MODE_2";
                            switchAIMode.checked = true;
                            AIModeSelect.disabled = false;
                            //rangeSliderAIVoltage.disabled = false;
                            AIVoltageBlock.hidden = true;
                            AIAutoBlock.hidden = false;
                            AIPowerBlock.hidden = true; 

                        }
                        else if (dataMain.aiStatus == 3) 
                        {
                            AIModeSelect.value = "AI_MODE_3";
                            switchAIMode.checked = true;
                            AIModeSelect.disabled = false;
                            //rangeSliderAIVoltage.disabled = false;
                            AIVoltageBlock.hidden = true;
                            AIAutoBlock.hidden = true;
                            AIPowerBlock.hidden = false; 
                        } 
                        else 
                        {
                            AIModeSelect.value = "AI_MODE_1";
                            switchAIMode.checked = false;
                            AIModeSelect.disabled = true;
                            //rangeSliderAIVoltage.disabled = true;
                            AIVoltageBlock.hidden = true;
                            AIAutoBlock.hidden = true;
                            AIPowerBlock.hidden = true; 
                        }
                    }
                    
                    /* Adaptation voltage */
                    if (dataMain.hasOwnProperty('aiVoltage')) 
                    {
                        if(Debounce.aiVoltage.ignoreFlag == 0)
                        {
                            EVSE.voltageAI = dataMain.aiVoltage;
                            AIvoltageValue.textContent = EVSE.voltageAI;
                            rangeSliderAIVoltage.value = EVSE.voltageAI;
                        }
                    }

                    /* Adaptation voltage start*/
                    if (dataMain.hasOwnProperty('aiVoltageStart')) 
                    {
                        EVSE.aiVoltageStart = dataMain.aiVoltageStart;
                        AIVoltageStart.textContent = EVSE.aiVoltageStart;
                    }

                    /* ADAPTIVE voltage drop*/
                    if (dataMain.hasOwnProperty('aiVoltageDrop')) 
                    {
                        if(dataMain.aiVoltageDrop > 0)
                        {
                            EVSE.aiVoltageDrop = dataMain.aiVoltageDrop;
                            AIVoltageDrop.textContent = ((100 * EVSE.aiVoltageDrop) / EVSE.aiVoltageStart).toFixed(0);
                        }
                        else
                        {
                            EVSE.aiVoltageDrop = 0;
                            AIVoltageDrop.textContent = 0;
                        }   
                    }

                    /* ADAPTIVE power drop*/
                    if (dataMain.hasOwnProperty('aiPowerDrop')) 
                    {
                        if(dataMain.aiPowerDrop > 0)
                        {
                            EVSE.aiPowerDrop = dataMain.aiPowerDrop;
                            AIPowerDrop.textContent = EVSE.aiPowerDrop;
                        }
                        else
                        {
                            EVSE.aiPowerDrop = 0;
                            AIPowerDrop.textContent = EVSE.aiPowerDrop;
                        }
                    }
                                                           
                    // /* Ground control */
                    // if (dataMain.hasOwnProperty('groundCtrl')) {
                    //     EVSE.groundCtrl = dataMain.groundCtrl;
                    //     switchControlPE.checked = EVSE.groundCtrl;
                    // }

                    if (dataMain.hasOwnProperty('a_ImbalC'))
                    {
                        EVSE.phase3Settings = dataMain.a_ImbalC;

                        if (dataMain.a_ImbalC == 2)
                        {
                            switch3PControl.checked = true;
                            ThreePhaseBalanceBlockSlider.hidden = true;
                        }
                        else if(dataMain.a_ImbalC == 0)
                        {
                            switch3PControl.checked = false;
                            ThreePhaseBalanceBlockSlider.hidden = false;
                        }
                        else
                        {
                            switch3PControl.checked = false;
                            ThreePhaseBalanceBlockSlider.hidden = false;
                        }
                    }

                    if (dataMain.hasOwnProperty('imbDeltaMax'))
                    {
                        if (Debounce.imbDeltaMax.ignoreFlag == 0)
                        {
                            EVSE.phase3Value = dataMain.imbDeltaMax;
                            phase3Value.textContent = EVSE.phase3Value;
                            range3PControl.value = EVSE.phase3Value;
                        }
                    }

                    /* Time limit status */
                    if (dataMain.hasOwnProperty('timeLimit')) {
                        if(Debounce.timeLimit.ignoreFlag == 0){
                            EVSE.timeLimit = dataMain.timeLimit;
                            if (EVSE.timeLimit < 500000){
                                timeLimitValue.textContent = secondsToStr(EVSE.timeLimit); 
                                rangeSliderTimeLimit.value = EVSE.timeLimit;
                            }
                            else{
                                timeLimitValue.textContent = secondsToStr(0); 
                                rangeSliderTimeLimit.value = EVSE.timeLimit;
                            }
                        }
                    }

                    /* Energy limit value */
                    if (dataMain.hasOwnProperty('energyLimit')) {
                        if(Debounce.energyLimit.ignoreFlag == 0){
                            EVSE.energyLimit = dataMain.energyLimit;
                            if (EVSE.energyLimit <= 100000){
                                energyLimitValue.textContent = (EVSE.energyLimit).toFixed(3); 
                                rangeSliderEnergyLimit.value = (EVSE.energyLimit * 10).toFixed(0);
                            }
                            else{
                                energyLimitValue.textContent = (0).toFixed(1); 
                                rangeSliderEnergyLimit.value = (EVSE.energyLimit * 10).toFixed(0);
                            }
                        }
                    }
                    
                    /* Money limit value */
                    if (dataMain.hasOwnProperty('moneyLimit')) {
                        if(Debounce.moneyLimit.ignoreFlag == 0)
                        {
                            EVSE.moneyLimit = dataMain.moneyLimit;
                            if (EVSE.moneyLimit <= 2000000)
                            {
                                moneyLimitValue.textContent = (EVSE.moneyLimit).toFixed(2); 
                                rangeSliderMoneyLimit.value = (EVSE.moneyLimit * 10).toFixed(0);
                            }
                            else
                            {
                                moneyLimitValue.textContent = (0).toFixed(2); 
                                rangeSliderMoneyLimit.value = (EVSE.moneyLimit * 10).toFixed(0);
                            }
                        }
                    }
                 

                    /* One charge status */ 
                    if (dataMain.hasOwnProperty('oneCharge')) {
                        EVSE.oneCharge = dataMain.oneCharge;
                        (EVSE.oneCharge) ? switchOneCharge.checked = 1 : switchOneCharge.checked = 0;
                    }


                }   /* ~Need init */

                /*------------------------------- Regular recieve data ------------------------------------*/
                if (ignoreCount == 0) {


                    if (dataMain.hasOwnProperty("curDesign")){
                        if(EVSE.evseDesignCurrent != dataMain.curDesign)
                        {
                            EVSE.evseDesignCurrent = dataMain.curDesign;
                            rangeSliderCurrent.max = EVSE.evseDesignCurrent;
                            sch1_range_slider_current.max = EVSE.evseDesignCurrent;
                            sch2_range_slider_current.max = EVSE.evseDesignCurrent;
                            // console.log(dataMain.curDesign);
                        }
                    }
                    
                    // /* SN */
                    if (dataMain.hasOwnProperty("serialNum")){
                        EVSE.serialNum = dataMain.serialNum;
                        serialNum.innerHTML  = "SN: "+EVSE.serialNum;
                      }

                    // /* Id */
                    // if (dataMain.hasOwnProperty("stationId")){
                    //     EVSE.stationId = dataMain.stationId;
                    //     stationId.innerHTML  = "ID:"+EVSE.stationId;
                    // }
                    
                    /*  Version */
                    if (dataMain.hasOwnProperty("verFWMain")){
                        EVSE.verFWMain = dataMain.verFWMain;
                        verFWMain.innerHTML  = "EVSE Version: " + EVSE.verFWMain;

                    }

                    if (dataMain.hasOwnProperty("verFWWifi")){
                        EVSE.verFWWifi = dataMain.verFWWifi;
                        verFWWifi.innerHTML  = "WiFi Version: " + EVSE.verFWWifi;

                        if (EVSE.verFWWifi.startsWith('UM'))
                        {
                            adapterSection.style.visibility = 'visible';
                        }
                        else
                        {
                            adapterSection.style.visibility = 'hidden';
                        }

                        if (EVSE.verFWWifi.startsWith('UE'))
                        {
                            phaseImbalaceBlock.style.display = 'block';
                        }
                        else
                        {
                            phaseImbalaceBlock.style.display = 'none';
                        }

                    }

                    if (dataMain.hasOwnProperty("thirdPartyBackends")){
                        EVSE.thirdPartyBackends = dataMain.thirdPartyBackends;
                        if(EVSE.thirdPartyBackends == 0)
                        {
                            OCPPConfigBlock.style.display = 'none';
                        }
                        else
                        {
                            OCPPConfigBlock.style.display = 'block';
                        }
                    }
                    
                    /* Security Status */
                    if (dataMain.hasOwnProperty("verFWStatus")){
                        if(dataMain.verFWStatus == 0){
                            verFWMain.style.color = "red";
                            verFWWifi.style.color = "red";
                        }
                        else
                        {
                            verFWMain.style.color = "white";
                            verFWWifi.style.color = "white";  
                        }
                    }
                    
                    /* Grid range value  */
                    if (dataMain.hasOwnProperty("gridRange"))
                        {
                            if( EVSE.gridRange != dataMain.gridRange)
                            {
                                EVSE.gridRange = dataMain.gridRange;
    
                                // Clear min voltage select
                                removeSelectOptions(minVoltageValue);
                                
                                
                                if(dataMain.gridRange  == 0)
                                {
                                    // Set new data to voltage range slider
                                    //rangeSliderAIVoltage.min = 180;
                                    rangeSliderAIVoltage.max = 220;
                                    
                                    
                                    // Set new data to min voltage select
                                    addSelectOptions(minVoltageValue, "200", 200);
                                    addSelectOptions(minVoltageValue, "150", 150);
                                    addSelectOptions(minVoltageValue, "155", 155);
                                    addSelectOptions(minVoltageValue, "160", 160);
                                    addSelectOptions(minVoltageValue, "165", 165);
                                    addSelectOptions(minVoltageValue, "170", 170);
                                    addSelectOptions(minVoltageValue, "175", 175);
                                    addSelectOptions(minVoltageValue, "180", 180);
                                    
                                    // rangeSliderCurrent.max = EVSE.evseDesignCurrent;
                                    // sch1_range_slider_current.max = EVSE.evseDesignCurrent;
                                    // sch2_range_slider_current.max = EVSE.evseDesignCurrent;
    
                                }
                                else if(dataMain.gridRange  == 1)
                                {   
                                    // Set new data to voltage range slider
                                    //rangeSliderAIVoltage.min = 90;
                                    
                                    rangeSliderAIVoltage.max = 110;
                                    
    
                                    // Set new data to min voltage select
                                    addSelectOptions(minVoltageValue, "95", 95);
                                    addSelectOptions(minVoltageValue, "75", 75);
                                    addSelectOptions(minVoltageValue, "80", 80);
                                    addSelectOptions(minVoltageValue, "85", 85);
                                    addSelectOptions(minVoltageValue, "90", 90);

                                }
                            }
                        }

                    /* MinVoltage value  */
                    if (dataMain.hasOwnProperty("minVoltage")){
                        minVoltageValue.value = dataMain.minVoltage + "";
                        rangeSliderAIVoltage.min =  dataMain.minVoltage + 10;
                    }


                    /* Lang type  */
                    if (dataMain.hasOwnProperty("lang")) {
                        if(EVSE.language != dataMain.lang) {
                            EVSE.language = dataMain.lang;
                            languageValue.value = langList[EVSE.language];
                            changeLang(EVSE.language);
                        }
                    }


                    /* Local IP */
                    if (dataMain.hasOwnProperty("STA_IP_Addres")){
                        EVSE.localIP = dataMain.STA_IP_Addres;
                        localIpValue.value =  EVSE.localIP;
                    }
                    
                    /* Current design */
                    // if (dataMain.hasOwnProperty("curDesign")) {
                    //     EVSE.evseDesignCurrent = dataMain.curDesign;
                    // }

                    /* AI current */
                    if (dataMain.hasOwnProperty('aiModecurrent')) {
                        EVSE.aiModeCurrent = dataMain.aiModecurrent;
                    }

                    //  /* ADAPTER  */
                    //  if (dataMain.hasOwnProperty("adapter")) {
                    //     EVSE.adapter = dataMain.adapter;
                    //     if (EVSE.adapter <= 12) 
                    //     {
                    //         rangeSliderCurrent.max = 12;
                    //         sch1_range_slider_current.max = 12;
                    //         sch2_range_slider_current.max = 12;
                    //     } 
                    //     else if (EVSE.adapter != 255)
                    //     {
                    //         rangeSliderCurrent.max = EVSE.evseDesignCurrent;
                    //         sch1_range_slider_current.max = EVSE.evseDesignCurrent;
                    //         sch2_range_slider_current.max = EVSE.evseDesignCurrent;
                    //     }
                        
                    // }
                    /* Current set */
                    if (dataMain.hasOwnProperty('currentSet')) {
                        if(Debounce.currentSet.ignoreFlag == 0)
                        {
                            EVSE.currentSet = dataMain.currentSet;
                            rangeSliderCurrent.value = EVSE.currentSet;
                            // if (EVSE.gridRange == 1)
                            // {
                            //     if (EVSE.adapterEnabled == 0)
                            //     {
                            //         if ((EVSE.currentSet > 12) ) {
                            //             EVSE.currentSet = 12;
                            //             rangeSliderCurrent.value = EVSE.currentSet;
                            //         } else {
                            //             rangeSliderCurrent.value = EVSE.currentSet;
                            //         }
                            //     }
                            //     else
                            //     {
                            //         if ((EVSE.currentSet > 24) ) {
                            //             EVSE.currentSet = 24;
                            //             rangeSliderCurrent.value = EVSE.currentSet;
                            //         } else {
                            //             rangeSliderCurrent.value = EVSE.currentSet;
                            //         }
                            //     }

                            // }


                            /* Current set */
                            if (switchAIMode.checked == true) {
                                //currentLimitValue.textContent = EVSE.aiModeCurrent + " /" + EVSE.currentSet;
                                for(var i = 0; i < currentLimitValue.length; i++)
                                { 
                                    currentLimitValue[i].textContent = EVSE.aiModeCurrent + " /" + EVSE.currentSet;
                                }
                            } else {
                                //currentLimitValue.textContent = EVSE.currentSet;
                                for(var i = 0; i < currentLimitValue.length; i++)
                                { 
                                    currentLimitValue[i].textContent = EVSE.currentSet;
                                }
                            }
                        }
                        
                    }
                    
                    /* State */
                    if (dataMain.hasOwnProperty("state")) {                           
                        //statusValue.textContent = msg.state[dataMain.state];
                        
                        for(var i = 0; i < statusValue.length; i++)
                        { 
                            statusValue[i].textContent = msg.state[dataMain.state];
                        }
                    }
                    /* SubState */
                    if (dataMain.hasOwnProperty("subState")) {  
                        if(dataMain.state == 7)
                        {
                            if(EVSE.language == 0)
                            {
                                rowNameSubStatus.innerHTML = "Ð¡ÑÐ°ÑÑÑ Ð¿Ð¾Ð¼Ð¸Ð»ÐºÐ¸";
                            }
                            else if(EVSE.language == 1)
                            {
                                rowNameSubStatus.innerHTML = "Error Status";
                            }                      
                            subStatusValue.textContent = msg.subStateError[dataMain.subState];
                        }
                        else
                        {
                            if(EVSE.language == 0)
                            {
                                rowNameSubStatus.innerHTML = "Ð¡ÑÐ°ÑÑÑ Ð»ÑÐ¼ÑÑÑ";
                            }
                            else if(EVSE.language == 1)
                            {
                                rowNameSubStatus.innerHTML = "Limit Status";
                            } 
                                
                            subStatusValue.textContent = msg.subStateLimit[dataMain.subState];
                        }
                    }

                    /* Connect to car*/
                    if(dataMain.hasOwnProperty("pilot"))
                    {
                        switch (dataMain.pilot) 
                        {
                            case 0x00: //evseStateA
                                pilotValue.textContent = msg.pilot.disconnected;
                                break;
                            case 0x01: //evseStateB
                            case 0x02: //evseStateC
                                pilotValue.textContent = msg.pilot.connected;
                                break;
                            default:
                                pilotValue.textContent = msg.pilot.unknown;
                                break;

                        }
                    }

                    /* EvseType*/
                    if (dataMain.hasOwnProperty("typeEvse")) {
                        EVSE.typeEvse = dataMain.typeEvse;
                    }
                    
                    /* Meter*/

                    if (dataMain.hasOwnProperty("voltMeas1") &&
                        dataMain.hasOwnProperty("voltMeas2") &&
                        dataMain.hasOwnProperty("voltMeas3")) 
                    {
                        //voltageValue.textContent = "";

                        for(var i = 0; i < voltageValue.length; i++)
                        { 
                            voltageValue[i].textContent = "";
                        }              

                        EVSE.voltMeas1 = dataMain.voltMeas1;
                        EVSE.voltMeas2 = dataMain.voltMeas2;
                        EVSE.voltMeas3 = dataMain.voltMeas3;
                        
                        if (EVSE.typeEvse == 2) 
                        {
                            for(var i = 0; i < voltageValue.length; i++)
                            { 
                                voltageValue[i].textContent = EVSE.voltMeas1.toFixed(0) + " " + EVSE.voltMeas2.toFixed(0) + " " + EVSE.voltMeas3.toFixed(0);
                            }
                        } 
                        else 
                        {
                            for(var i = 0; i < voltageValue.length; i++)
                            { 
                                voltageValue[i].textContent = EVSE.voltMeas1.toFixed(0) + "";
                            }
                            EVSE.voltMeas2 = 0;
                            EVSE.voltMeas3 = 0;
                        }


                    }

                    if (dataMain.hasOwnProperty("curMeas1") &&
                        dataMain.hasOwnProperty("curMeas2") &&
                        dataMain.hasOwnProperty("curMeas3")) {
                        currentValue.textContent = '';
                        
                        EVSE.curMeas1 = (dataMain.curMeas1);
                        EVSE.curMeas2 = (dataMain.curMeas2);
                        EVSE.curMeas3 = (dataMain.curMeas3);
                        
                        
                        if(EVSE.typeEvse == 2) 
                        {
                            for(var i = 0; i < currentValue.length; i++)
                            { 
                                currentValue[i].textContent = EVSE.curMeas1.toFixed(1) + " " + EVSE.curMeas2.toFixed(1) + " " + EVSE.curMeas3.toFixed(1);
                            }
                        } 
                        else 
                        {
                            for(var i = 0; i < currentValue.length; i++)
                            { 
                                currentValue[i].textContent = EVSE.curMeas1.toFixed(1) + "";
                            }
                            EVSE.curMeas2 = 0;
                            EVSE.curMeas3 = 0;
                        }
                    }

                    /* POWER  */
                    if (dataMain.hasOwnProperty("powerMeas")) {
                        EVSE.powerMeas = dataMain.powerMeas;
                        //powerValue.textContent = (dataMain.powerMeas / 1000).toFixed(1);
                        for(var i = 0; i < powerValue.length; i++){
                            powerValue[i].textContent = (dataMain.powerMeas / 1000).toFixed(1);
                        }
                    }
                    
                    /* TEMPERATURE  */
                    if (dataMain.hasOwnProperty("temperature1") &&
                        dataMain.hasOwnProperty("temperature2")) {
                        EVSE.temp1 = dataMain.temperature1;
                        EVSE.temp2 = dataMain.temperature2;

                        if(EVSE.temp1 < -50){
                            (temperatureBoxValue.textContent = "N/A") 
                            EVSE.temp1 = 0;
                        }else{
                            (temperatureBoxValue.textContent = dataMain.temperature1);
                        }

                        if(EVSE.temp2 < -50){
                            (temperatureSocketValue.textContent = "N/A") 
                            EVSE.temp2 = 0;
                        }else{ 
                            (temperatureSocketValue.textContent = dataMain.temperature2);
                        }
                    }
                    
                    /* SERSSION ENERGY */
                    if (dataMain.hasOwnProperty("sessionEnergy")) {
                        sessionEnergyValue.textContent = (dataMain.sessionEnergy).toFixed(1);
                    }

                    /* SESSION TIME */
                    if (dataMain.hasOwnProperty("sessionTime")) {
                        let hours, minutes, secunds;
                        EVSE.sessionTime = Number(dataMain.sessionTime);
                        sessionTimeValue.textContent = secondsToStr(EVSE.sessionTime);
                    }
                    
                    /* SESSION MONEY */
                    if (dataMain.hasOwnProperty("sessionMoney")) {
                        EVSE.session_money = dataMain.sessionMoney;
                        sessionMoneyValue.textContent = EVSE.session_money.toFixed(1);
                    }
                    
                    /* TOTAL ENERGY */
                    if (dataMain.hasOwnProperty("totalEnergy")) {
                        totalEnergyValue.textContent = (dataMain.totalEnergy).toFixed(1);
                    }

                    /* INDEPENDED ENERGY METER 1 */
                    if (dataMain.hasOwnProperty("IEM1")) {
                        IEM1Value.textContent = (dataMain.IEM1).toFixed(1);
                    }
                    if (dataMain.hasOwnProperty("IEM1_money")) {
                        IEM1Money.textContent = (dataMain.IEM1_money).toFixed(1);
                    }

                    /* INDEPENDED ENERGY METER 2 */
                    if (dataMain.hasOwnProperty("IEM2")) {
                        IEM2Value.textContent = (dataMain.IEM2).toFixed(1);
                    }
                    if (dataMain.hasOwnProperty("IEM2_money")) {
                        IEM2Money.textContent = (dataMain.IEM2_money).toFixed(1);
                    }

                    /* ADAPTIVE STATUS */
                    if (dataMain.hasOwnProperty("aiStatus")){
                        
                        EVSE.aiMode = dataMain.aiStatus;
                        
                        if (dataMain.aiStatus == 1) 
                        {
                            AIModeSelect.value = "AI_MODE_1";
                            switchAIMode.checked = true;
                            //rangeSliderAIVoltage.disabled = false;
                            AIVoltageBlock.hidden = false;
                            AIAutoBlock.hidden = true;
                            AIPowerBlock.hidden = true; 
                        } 
                        else if (dataMain.aiStatus == 2) 
                        {
                            AIModeSelect.value = "AI_MODE_2";
                            switchAIMode.checked = true;
                            //rangeSliderAIVoltage.disabled = false;
                            AIVoltageBlock.hidden = true;
                            AIAutoBlock.hidden = false;
                            AIPowerBlock.hidden = true; 
                        }
                        else if (dataMain.aiStatus == 3) 
                        {
                            AIModeSelect.value = "AI_MODE_3";
                            switchAIMode.checked = true;
                            //rangeSliderAIVoltage.disabled = false;
                            AIVoltageBlock.hidden = true;
                            AIAutoBlock.hidden = true;
                            AIPowerBlock.hidden = false; 
                        }
                        else 
                        {
                            switchAIMode.checked = false;
                            //rangeSliderAIVoltage.disabled = true;
                            AIVoltageBlock.hidden = true;
                            AIAutoBlock.hidden = true;
                            AIPowerBlock.hidden = true; 
                        }
                    }

                    /* ADAPTIVE VOLTAGE */
                    if (dataMain.hasOwnProperty("aiVoltage")){
                        if(Debounce.aiVoltage.ignoreFlag == 0)
                        {
                            EVSE.voltageAI = dataMain.aiVoltage;
                            AIvoltageValue.textContent = EVSE.voltageAI;
                            rangeSliderAIVoltage.value = EVSE.voltageAI;
                        }
                    }

                    /* ADAPTIVE voltage start*/
                    if (dataMain.hasOwnProperty('aiVoltageStart')) 
                    {
                        EVSE.aiVoltageStart = dataMain.aiVoltageStart;
                        AIVoltageStart.textContent = EVSE.aiVoltageStart;
                    }

                    /* ADAPTIVE voltage drop*/
                    if (dataMain.hasOwnProperty('aiVoltageDrop')) 
                    {
                        if(dataMain.aiVoltageDrop > 0)
                        {
                            EVSE.aiVoltageDrop = dataMain.aiVoltageDrop;
                            AIVoltageDrop.textContent = ((100 * EVSE.aiVoltageDrop) / EVSE.aiVoltageStart).toFixed(0);
                        }
                        else
                        {
                            EVSE.aiVoltageDrop = 0;
                            AIVoltageDrop.textContent = 0;
                        }   
                    }

                    /* ADAPTIVE power drop*/
                    if (dataMain.hasOwnProperty('aiPowerDrop')) 
                    {
                        if(dataMain.aiPowerDrop > 0)
                        {
                            EVSE.aiPowerDrop = dataMain.aiPowerDrop;
                            AIPowerDrop.textContent = EVSE.aiPowerDrop;
                        }
                        else
                        {
                            EVSE.aiPowerDrop = 0;
                            AIPowerDrop.textContent = EVSE.aiPowerDrop;
                        }
                    }
                    
                   
                    /* GROUND   STATE */
                    if (dataMain.hasOwnProperty("ground")) {
                        EVSE.ground = dataMain.ground;
                        if (EVSE.ground == 1) {
                            controlPEValue.textContent = msg.pe_connect.connected;
                        } else {
                            controlPEValue.textContent = msg.pe_connect.disconnected;
                        }
                    }
                    // /* GROUND  CTRL */
                    // if (dataMain.hasOwnProperty("groundCtrl")) {
                    //     EVSE.groundCtrl = dataMain.groundCtrl;
                    //     switchControlPE.checked = EVSE.groundCtrl;
                    // }
                    
                    /* LEAKAGE */
                    if(dataMain.hasOwnProperty("leakValue")){
                        leakValue.textContent = dataMain.leakValue.toFixed(1);
                    }
                    
                    
                    /* TIMER TYPE  */
                    if (dataMain.hasOwnProperty("timerType")){
                        switch (dataMain.timerType) {
                            case 0:
                                timerTypeValue.value = "noPWM";
                                break;
                            case 1:
                                timerTypeValue.value = "VAG";
                                break;
                        }
                    }

                    // /* LIMITS STATUS */
                    // if (dataMain.hasOwnProperty("suspendErrors"))
                    // {
                    //     EVSE.suspendErrors = dataMain.suspendErrors;
                    //     switchSuspendErrors.checked = parseInt(EVSE.suspendErrors);
                    // }

                    if (dataMain.hasOwnProperty("suspendLimits"))
                    {
                        EVSE.suspendLimits = dataMain.suspendLimits;
                        switchSuspendLimits.checked = parseInt(EVSE.suspendLimits);
                    }

                    if (dataMain.hasOwnProperty("timeLimitS"))
                    {
                        EVSE.timeLimitS = dataMain.timeLimitS;
                        switchTimeLimit.checked = parseInt(EVSE.timeLimitS);
                    }
                    if (dataMain.hasOwnProperty("energyLimitS"))
                    {
                        EVSE.energyLimitS = dataMain.energyLimitS;
                        switchEnergyLimit.checked = parseInt(EVSE.energyLimitS);
                    }
                    if (dataMain.hasOwnProperty("moneyLimitS"))
                    {
                        EVSE.moneyLimitS = dataMain.moneyLimitS;
                        switchMoneyLimit.checked = parseInt(EVSE.moneyLimitS);
                    }
                    // if (dataMain.hasOwnProperty("delayedLimit"))
                    // {
                    //     EVSE.delayedLimit = dataMain.delayedLimit;
                    //     delayedLimitControl.checked = parseInt(EVSE.delayedLimit);
                    // }

                    

                    /* EVSE ENABLED */
                    if (dataMain.hasOwnProperty("evseEnabled")){
                        EVSE.evseEnabled = dataMain.evseEnabled;
                        if(EVSE.evseEnabled == 1){
                            switchEvseEnabled.checked = 1;
                        }else{
                            switchEvseEnabled.checked = 0;
                        }
                    }
                    if (dataMain.hasOwnProperty("adapterEnabled")){
                        EVSE.adapterEnabled = dataMain.adapterEnabled;
                        if(EVSE.adapterEnabled == 1){
                            switchAdapterChange.checked = 1;
                        }else{
                            switchAdapterChange.checked = 0;
                        }
                    }
                    
                    /* TIME LIMIT */
                    if (dataMain.hasOwnProperty("timeLimit")){
                        if(Debounce.timeLimit.ignoreFlag == 0){
                            EVSE.timeLimit = dataMain.timeLimit;
                            if(dataMain.timeLimit <= 500000){
                                rangeSliderTimeLimit.value = dataMain.timeLimit;
                                timeLimitValue.textContent = secondsToStr(dataMain.timeLimit);
                            }
                        }
                    }

                    /* ENERGY LIMIT */
                    if (dataMain.hasOwnProperty("energyLimit")){
                        if(Debounce.energyLimit.ignoreFlag == 0){
                            EVSE.energyLimit = dataMain.energyLimit;
                            if(dataMain.energyLimit <= 10000){
                                rangeSliderEnergyLimit.value = (dataMain.energyLimit*10).toFixed(0);
                                energyLimitValue.textContent = (dataMain.energyLimit).toFixed(3);
                            }
                        }
                    }
                    
                    /* MONEY LIMIT */
                    if (dataMain.hasOwnProperty("moneyLimit")){
                        if(Debounce.moneyLimit.ignoreFlag == 0){
                            EVSE.moneyLimit = dataMain.moneyLimit;
                            if(dataMain.moneyLimit <= 20000){
                                rangeSliderMoneyLimit.value = (dataMain.moneyLimit*10).toFixed(0);
                                moneyLimitValue.textContent = (dataMain.moneyLimit).toFixed(2);
                            }
                        }
                    }
                                        
                    /* TARIF 1 */
                    if (dataMain.hasOwnProperty("tarif")){
                        if (!allowDataSending) { return;}
                            if(dataMain.tarif  <= 10000){
                            EVSE.tarif_1 = dataMain.tarif;
                            tarif_1.value =  (dataMain.tarif / 100).toFixed(2); 
                            }
                          
                    }
                    
                    /* ACTIVE TARIF */
                    if (dataMain.hasOwnProperty("activeTarif")){
                        EVSE.activeTarif = dataMain.activeTarif;
                        
                        switch(EVSE.activeTarif)
                        {
                            case(0):
                                for(var i = 0; i < activeTarif.length; i++)
                                { 
                                   activeTarif[i].textContent = msg.tarif[0] + (EVSE.tarif_1 / 100).toFixed(2);
                                }
                                break; 
                            case(1):
                                for(var i = 0; i < activeTarif.length; i++)
                                { 
                                    activeTarif[i].textContent = msg.tarif[1] + (EVSE.tarifAValue / 100).toFixed(2);
                                }
                                break;
                            case(2):
                                for(var i = 0; i < activeTarif.length; i++)
                                { 
                                    activeTarif[i].textContent = msg.tarif[2] + (EVSE.tarifBValue / 100).toFixed(2);
                                }
                                break;

                        }                        
                    }

                    /* TARIF A Value */
                    if (dataMain.hasOwnProperty("tarifAValue")){
                        if (!allowDataSending) { return;}
                        if(dataMain.tarifAValue  <= 10000){
                            EVSE.tarifAValue = dataMain.tarifAValue;
                            tarifAValue.value =  (dataMain.tarifAValue / 100).toFixed(2); 
                        }
                    }                 
                    /* TARIF A Enable */
                    if (dataMain.hasOwnProperty("tarifAEnable")){
                        EVSE.tarifAEnable = dataMain.tarifAEnable;
                        tarifAEnable.checked =  EVSE.tarifAEnable;
                    }
                    /* TARIF A START */
                    if (dataMain.hasOwnProperty("tarifAStart")){
                        if (!allowDataSending) { return;}
                        EVSE.tarifAStart = secondsToStr(dataMain.tarifAStart * 60);
                        tarifAStart.value = EVSE.tarifAStart;
                    }
                    /* TARIF A STOP */
                    if (dataMain.hasOwnProperty("tarifAStop")){
                        if (!allowDataSending) { return;}
                        EVSE.tarifAStop = secondsToStr(dataMain.tarifAStop * 60);
                        tarifAStop.value = EVSE.tarifAStop;
                    }

                    /* TARIF B Value */
                    if (dataMain.hasOwnProperty("tarifBValue")){
                        if (!allowDataSending) { return;}
                        if(dataMain.tarifBValue  <= 10000){
                            EVSE.tarifBValue = dataMain.tarifBValue;
                            tarifBValue.value =  (dataMain.tarifBValue / 100).toFixed(2); 
                        }
                    }                 
                    /* TARIF B Enable */
                    if (dataMain.hasOwnProperty("tarifBEnable")){
                        EVSE.tarifBEnable = dataMain.tarifBEnable;
                        tarifBEnable.checked =  EVSE.tarifBEnable;
                    }
                    /* TARIF B START */
                    if (dataMain.hasOwnProperty("tarifBStart")){
                        if (!allowDataSending) { return;}
                        EVSE.tarifBStart = secondsToStr(dataMain.tarifBStart * 60);
                        tarifBStart.value = EVSE.tarifBStart;
                    }
                    /* TARIF B STOP */
                    if (dataMain.hasOwnProperty("tarifBStop")){
                        if (!allowDataSending) { return;}
                        EVSE.tarifBStop = secondsToStr(dataMain.tarifBStop * 60);
                        tarifBStop.value = EVSE.tarifBStop;
                    }




                    /* ONE CHARGE STATUS */
                    if (dataMain.hasOwnProperty("oneCharge")){
                        EVSE.oneCharge = dataMain.oneCharge;
                        switchOneCharge.checked = EVSE.oneCharge;
                    } else {
                        EVSE.oneCharge = 0;
                        switchOneCharge.checked = 0;
                    }

                    /* SCHEDULE 1 ENABLED */
                    if (dataMain.hasOwnProperty("sh1Enabled")){
                        EVSE.sh1Enabled = dataMain.sh1Enabled;
                        switchSchedule1.checked = parseInt(EVSE.sh1Enabled);
                    }

                    /* SCHEDULE 1 START */
                    if (dataMain.hasOwnProperty("sh1Start")){
                        if (!allowDataSending) { return;}
                        EVSE.sh1Start = dataMain.sh1Start;
                        startSchedule1.value = secondsToStr(EVSE.sh1Start * 60);
                    }
                    
                    /* SCHEDULE 1 STOP */
                    if (dataMain.hasOwnProperty("sh1Stop")){
                        if (!allowDataSending) { return;}
                        EVSE.sh1Stop = dataMain.sh1Stop;
                        stopSchedule1.value = secondsToStr(EVSE.sh1Stop * 60);
                    }
                    
                    /* SCHEDULE 1 CURRENT ENABLE */
                    if (dataMain.hasOwnProperty("sh1CurrentEnable")){
                        EVSE.sh1CurrentEnable = dataMain.sh1CurrentEnable;
                        sch1_switch_current.checked = parseInt(EVSE.sh1CurrentEnable);
                    }

                    /* SCHEDULE 1 CURRENT  VALUE*/
                    if (dataMain.hasOwnProperty("sh1CurrentValue")){
                        
                        if(Debounce.sh1CurrentValue.ignoreFlag == 0)
                        {
                            EVSE.sh1CurrentValue = dataMain.sh1CurrentValue;
                            sch1_range_slider_current.value = EVSE.sh1CurrentValue;
                            sch1_current_limit_value.textContent = EVSE.sh1CurrentValue;
                        }
                    }
                    
                    /* SCHEDULE 1 ENERGY ENABLE */
                    if (dataMain.hasOwnProperty("sh1EnergyEnable")){
                        EVSE.sh1EnergyEnable = dataMain.sh1EnergyEnable;
                        sch1_switch_energy.checked = parseInt(EVSE.sh1EnergyEnable);
                    }

                    /* SCHEDULE 1 ENERGY VALUE*/
                    if (dataMain.hasOwnProperty("sh1EnergyValue")){
                        if(Debounce.sh1EnergyValue.ignoreFlag == 0){
                            EVSE.sh1EnergyValue = dataMain.sh1EnergyValue;
                            sch1_range_slider_energy.value = (EVSE.sh1EnergyValue*10).toFixed(0);
                            sch1_energy_limit_value.textContent = (EVSE.sh1EnergyValue).toFixed(3);
                        }
                    }

                    /* SCHEDULE 2 ENABLED */
                    if (dataMain.hasOwnProperty("sh2Enabled")){
                        EVSE.sh2Enabled = dataMain.sh2Enabled;
                        switchSchedule2.checked = parseInt(EVSE.sh2Enabled);
                    }

                    /* SCHEDULE 2 START */
                    if (dataMain.hasOwnProperty("sh2Start")){
                        if (!allowDataSending) { return;}
                        EVSE.sh2Start = dataMain.sh2Start;
                        startSchedule2.value = secondsToStr(EVSE.sh2Start * 60);
                    }
                    
                    /* SCHEDULE 2 STOP */
                    if (dataMain.hasOwnProperty("sh2Stop")){
                        if (!allowDataSending) { return;}
                        EVSE.sh2Stop = dataMain.sh2Stop;
                        stopSchedule2.value = secondsToStr(EVSE.sh2Stop * 60);
                    }
                    
                    /* SCHEDULE 2 CURRENT ENABLE */
                    if (dataMain.hasOwnProperty("sh2CurrentEnable")){
                        EVSE.sh2CurrentEnable = dataMain.sh2CurrentEnable;
                        sch2_switch_current.checked = parseInt(EVSE.sh2CurrentEnable);
                    }

                    /* SCHEDULE 2 CURRENT VALUE*/
                    if (dataMain.hasOwnProperty("sh2CurrentValue")){
                        if(Debounce.sh2CurrentValue.ignoreFlag == 0){
                            EVSE.sh2CurrentValue = dataMain.sh2CurrentValue;
                            sch2_range_slider_current.value = EVSE.sh2CurrentValue;
                            sch2_current_limit_value.textContent = EVSE.sh2CurrentValue;
                        }
                    }

                    /* SCHEDULE 2 ENERGY ENABLE */
                    if (dataMain.hasOwnProperty("sh2EnergyEnable")){
                        EVSE.sh2EnergyEnable = dataMain.sh2EnergyEnable;
                        sch2_switch_energy.checked = parseInt(EVSE.sh2EnergyEnable);
                    }
                    
                    /* SCHEDULE 2 ENERGY VALUE*/
                    if (dataMain.hasOwnProperty("sh2EnergyValue")){
                        if(Debounce.sh2EnergyValue.ignoreFlag == 0){
                            EVSE.sh2EnergyValue = dataMain.sh2EnergyValue;
                            sch2_range_slider_energy.value = (EVSE.sh2EnergyValue*10).toFixed(0);
                            sch2_energy_limit_value.textContent = (EVSE.sh2EnergyValue).toFixed(3);
                        }
                    }

              
                    /* SCAN STATUS */
                    if (dataMain.hasOwnProperty("scanComplete")){
                        if(dataMain.scanComplete == 1)
                        {   
                            if(EVSE.blockScanResult == false)
                            {
                                EVSE.blockScanResult = true;
                                checkScanResult();
                            }
                        }
                    }

                    /* TIME MSG */
                    if (dataMain.hasOwnProperty("timeMsg")){
                        if(dataMain.timeMsg == 1)
                        {
                            if(document.getElementById('TimeMessage') != null )
                                document.getElementById('TimeMessage').innerHTML = 'System time unavaliable. Please check battery, or contact service.';
                        }
                        else
                        {
                            if(document.getElementById('TimeMessage') != null )
                                document.getElementById('TimeMessage').innerHTML = '';
                        }
                    }
                    
                    /* SYSTEM TIME */
                    if (dataMain.hasOwnProperty("systemTime")){
                        EVSE.systemTime = dataMain.systemTime;
                        systemTime.value = secondsToStr(EVSE.systemTime);
                    }

                    /* TIME ZONE */
                    if (dataMain.hasOwnProperty("timeZone")){
                        if (EVSE.prevTimeZone != dataMain.timeZone)
                        {
                            EVSE.prevTimeZone = dataMain.timeZone;
                            EVSE.timeZone = dataMain.timeZone;
                            timeZoneValue.value = EVSE.timeZone;
                        }
                    }

                    /* LOG */
                    if (dataMain.hasOwnProperty("logReady")){
                        if (dataMain.logReady)
                        {
                            checkGetLogResult();
                        }
                    }

                    if(EVSE.reconnectFlag == true)
                    {
                        EVSE.reconnectFlag = false;
                        EVSE.reconnectTime = 0;
                        if(document.getElementById('ConnectionMessage') != null )
                        document.getElementById('ConnectionMessage').innerHTML = "";
                    }

                    if (dataMain.hasOwnProperty("ocppEnabled")){
                        if(EVSE.ocppEnabled != dataMain.ocppEnabled){
                            EVSE.ocppEnabled = dataMain.ocppEnabled;
                            ocppEnabled.checked = parseInt(EVSE.ocppEnabled);
                        }
                    }

                    if (dataMain.hasOwnProperty("ocppOfflineAva")){
                        if(EVSE.ocppOfflineAva != dataMain.ocppOfflineAva){
                            EVSE.ocppOfflineAva = dataMain.ocppOfflineAva;
                            ocppOfflineAva.checked = parseInt(EVSE.ocppOfflineAva);
                        }
                    }
                    
                    if (dataMain.hasOwnProperty("ocppConnected")){
                            EVSE.ocppConnected = dataMain.ocppConnected;
                            if(EVSE.ocppConnected == 1){
                                ocppConnected.textContent = msg.ocpp.connected;
                            }
                            else{
                                ocppConnected.textContent = msg.ocpp.disconnected;
                            }
                    }                    

                } /* Regular data */
                
                if (ignoreCount) {
                    ignoreCount--;
                }

                if(EVSE.reconnectFlag == true)
                {
                    EVSE.reconnectTime = EVSE.reconnectTime + 1;
                    if(document.getElementById('ConnectionMessage') != null )
                    document.getElementById('ConnectionMessage').innerHTML = 
                    `<div class="col-8 days redRow"> Reconnecting... EVSE.reconnectTime</div>
                    <div class="col-4 d-flex justify-content-end days redRow">
                       <button class="btn1" onclick="resetPostPageEvent()">Retry</button>
                    </div>`
                }
            }
        }
    }
}
/* postDataMain */
/*-----------------------------------------------------------------------------------------*/
function HandleConnectionLost()
{
    if(countNoConnection < 5) {
        countNoConnection ++;
    }
    else {
        ShowOfflineMessageDiv();
    }
}
/*-----------------------------------------------------------------------------------------*/

function HandleConnectionRecovery()
{
    if(countNoConnection != 0) {
        countNoConnection = 0;
        HideOfflineMessageDiv();
    }
}
/*-----------------------------------------------------------------------------------------*/

function ShowOfflineMessageDiv() { 
    if(document.getElementById("offlineDiv").style.display != "block")
        console.log("OFFLINE");
        document.getElementById("offlineDiv").style.display = "block";
}


/*-----------------------------------------------------------------------------------------*/
function HideOfflineMessageDiv(){
    if(document.getElementById("offlineDiv").style.display != "none")
        console.log("ONLINE");
        document.getElementById("offlineDiv").style.display = "none";
}
/*-----------------------------------------------------------------------------------------*/
function resetPostPageEvent()
{

    EVSE.reconnectFlag = true;
    EVSE.reconnectTime = 0;

    if(document.getElementById('ConnectionMessage') != null )
                    document.getElementById('ConnectionMessage').innerHTML =
                    `<div class="col-8 days redRow"> Reconnecting...</div>
                    <div class="col-4 d-flex justify-content-end days redRow">
                       <button class="btn1" onclick="resetPostPageEvent()">Retry</button>
                    </div>`;

    mainTimer = setInterval(function () { postDataMain();}, 1000);
    postDataMain();
}

/*-----------------------------------------------------------------------------------------*/
/*                          test Rx data validattion                                       */
/*-----------------------------------------------------------------------------------------*/ 
function testValid(req) {
    let result = true;

    // if ((req.currentSet < 6) || (req.currentSet > EVSE.evseDesignCurrent)) {
    //     console.log("CurrentSet:"+req.currentSet + " " +EVSE.evseDesignCurrent);
    //     result = false;
    // }
    // if (req.state > 50) {
    //     console.log("State:"+req.state);
    //     result = false;
    // }
    // if ((req.curMeas1 > 800) || (req.curMeas2 > 800) || (req.curMeas3 > 800)) {
    //     console.log("Meas C: "+req.curMeas1 +" "+req.curMeas2+" "+req.curMeas3);
    //     result = false;
    // }
    // if ((req.voltMeas1 > 350) || (req.voltMeas2 > 350) || (req.voltMeas3 > 350)) {
    //     console.log("Meas V: "+req.voltMeas1 +" "+req.voltMeas2+" "+req.voltMeas3);
    //     result = false;
    // }
    // if (req.timer > 86400) {
    //     console.log("Timer : "+req.timer);
    //     result = false;
    // }

    // if (req.aiModecurrent > EVSE.evseDesignCurrent) {
    //     console.log("aiModecurrent : "+req.aiModecurrent);
    //     result = false;
    // }
    // if (req.aiStatus > 5) {
    //     console.log("aiStatus : "+req.aiStatus);
    //     result = false;
    // }
    // if (req.aiVoltage > 220) {
    //     console.log("aiVoltage : "+req.aiVoltage);
    //     result = false;
    // }
    // // if (req.sessionEnergy > 10000) {
    // //     result = false;
    // // }
    // // if ((req.temperature1 < -80) || (req.temperature1 > 150)) {
    // //     result = false;
    // // }
    // if (req.ground > 1) {
    //     console.log("ground : "+req.ground);
    //     result = false;
    // }
    // if (req.curDesign > 80) {
    //     console.log("curDesign : "+req.curDesign);
    //     result = false;
    //}
    return result;
} /* TestValid */


/*-----------------------------------------------------------------------------------------*/
/*                                 Post pageEvent                                          */
/*                          Sends data to /pageEvent                                       */
/*-----------------------------------------------------------------------------------------*/ 
function postPageEvent(name, value, cnt = 2) {
    let request = new XMLHttpRequest();
    request.open("POST", "/pageEvent", true);
    request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    request.setRequestHeader("pageEvent", name);
    request.send(name + "=" + value);
    ignoreCount = cnt;
}

function postPageEventSeveral(req) {
    let request = new XMLHttpRequest();
    request.open("POST", "/pageEvent", true);
    request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    request.send(req);
    ignoreCount = 2;
}


function checkScanResult()
{
    let requestScanRes = new XMLHttpRequest();
    requestScanRes.open("POST", "/scanResult", true);
    requestScanRes.send();
    
    requestScanRes.onreadystatechange = function() 
    {
        if (requestScanRes.readyState == 4 && requestScanRes.status == 200) 
        {
            //txtlistNets.innerHTML = requestScanRes.responseText; // OLD


            const scanRes = JSON.parse(requestScanRes.responseText);
            console.log(scanRes);
            txtlistNets.innerHTML = scanRes.map((scanRes) => `
            <p>
                <b><a class="nameNet" onclick="focusFunction()">${scanRes.name.toString()}</a></b>
                [RSSI:${scanRes.rssi.toString()}] 
                [<a class="nameMAC" href="#">${scanRes.mac.toString()}</a>]
            </p>`
            ).join("");
        }
    }
}

function checkGetLogResult()
{
    let requestLogRes = new XMLHttpRequest();
    requestLogRes.open("POST", "/get_logResult", true);
    requestLogRes.send();
  
    requestLogRes.onreadystatechange = function() 
    {
      if (requestLogRes.readyState == 4 && requestLogRes.status == 200) 
      {
        
            const log = JSON.parse(requestLogRes.responseText);
            //console.log(log);
            txtlistLogs.innerHTML = log.map((log) => `
            <div class="row statisticRow">
                <div class="col-3">
                ${log.log_dd.toString().padStart(2, "0")}/${log.log_mnth.toString().padStart(2, "0")} 
                ${log.log_hh.toString().padStart(2, "0")}:${log.log_mm.toString().padStart(2, "0")}:${log.log_sec.toString().padStart(2, "0")}
                </div>

                <div class="col-3">${log.s_enrg.toFixed(1)}</div>
                <div class="col-3">
                ${log.s_hh.toString().padStart(2, "0")}:${log.s_mm.toString().padStart(2, "0")}:${log.s_sec.toString().padStart(2, "0")}
                </div>
                <div class="col-3">${log.s_cost.toFixed(2)}</div>
            </div>`
            ).join("");
        }
    }
}

/* Other functions */
function n(e) {
    for (let t = e; t < tabContent.length; t++) tabContent[t].classList.add("d-none");
}

n(1);
function changeTab(num)
{
    n(0); 
    if(tabContent[num].classList.contains("d-none"))
    {
        tabContent[num].classList.remove("d-none");
    }
}


// ERRORS //
function DisplayErrorMessage(objectName, text, color = 'black')
{
    if(document.getElementById(objectName) != null )
    {
        document.getElementById(objectName).innerHTML = text;
        document.getElementById(objectName).style.color = color;
    }
}

function CheckApSettings()
{
    if(isASCII(EVSE.ssidNameAP) == false || isASCII(EVSE.ssidPasswordAP) == false)
    {
        DisplayErrorMessage("WiFiAPSaveMessage", msg.wifiErrorASCII, 'red');
        return false;
    }

    // if (EVSE.WifiMode == 2)
    // {
    //     DisplayErrorMessage("WiFiAPSaveMessage", msg.wifiBroadcastAPError, 'red');
    //     return false;
    // }

    if(EVSE.ssidNameAP.length == 1)
    {
        DisplayErrorMessage("WiFiAPSaveMessage", msg.wifiErrorName, 'red');
        return false;
    }
    
    if(EVSE.ssidPasswordAP.length != 0 && EVSE.ssidPasswordAP.length < 8)
    {
        DisplayErrorMessage("WiFiAPSaveMessage", msg.wifiErrorPass, 'red');
        return false;
    }
    
    if(EVSE.ssidPasswordAP != EVSE.ssidPasswordAPConf)
    {
        DisplayErrorMessage("WiFiAPSaveMessage", msg.wifiErrorPassConf, 'red');
        return false;
    }
    return true;

}

function CheckPageSettings()
{
    if(isASCII(EVSE.httpUsername) == false || isASCII(EVSE.httpPassword) == false)
    {
        DisplayErrorMessage("HTMLSaveMessage", msg.wifiErrorASCII, 'red');
        return false;
    }

    if(EVSE.httpUsername == "" &&  EVSE.httpPassword != "")
    {
        DisplayErrorMessage("HTMLSaveMessage", msg.wifiHTTPNameError, 'Red');
        return false;
    }
    
    if(EVSE.httpPassword != EVSE.httpPasswordConf)
    {
        DisplayErrorMessage("HTMLSaveMessage", msg.wifiErrorPassConf, 'Red');
        return false;
    }
    
    return true;
}  

function CheckSTASettings()
{
    if(isASCII(EVSE.httpUsername) == false || isASCII(EVSE.httpPassword) == false)
    {
        DisplayErrorMessage("WiFiSTASaveMessage", msg.wifiErrorASCII, 'red');
        return false;
    }

    if(EVSE.ssidPassword.length != 0 && EVSE.ssidPassword.length < 8)
    {
        DisplayErrorMessage("WiFiSTASaveMessage", msg.wifiErrorPass, 'red');
        return false;
    }

    if (EVSE.STA_MAC.length != 0 && EVSE.STA_MAC.length < 17 || EVSE.STA_MAC.length != 0 && EVSE.STA_MAC.length > 17)
    {
        DisplayErrorMessage("WiFiSTASaveMessage", msg.wifiErrorSTAMAC, 'Red');
        return false;
    }
    
    return true;
}

function postPageOneEvent(name, value, CallbackFunction = undefined, cnt = 2) {
    let request = new XMLHttpRequest();
    request.open("POST", "/ocppEvent", true);
    request.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    request.setRequestHeader("pageEvent", name);
    request.send(name + "=" + value);
    ignoreCount = cnt;
    
    if(CallbackFunction === undefined) return;

    request.onreadystatechange = function() {
        if ((request.readyState == 4) && (request.status == 200)) {
            if(this.responseText.length > 0)
                CallbackFunction(this.responseText);
            else
             CallbackFunction("Request done!");
        }   
    }
  
}

// function showModal(descriptionKey) {
//     const language = languageValue.value; 
//     const description = descriptions[descriptionKey]?.[language] || descriptions[descriptionKey]?.["EN"]; // Fallback to English

//     const descriptionElement = document.querySelector("#popupModal .description");
//     descriptionElement.innerHTML = description;

//     descriptionElement.className = "description"; 
//     if (language === "UA") {
//         descriptionElement.classList.add("ua"); 
//     }
//     if (language === "FR") {
//         descriptionElement.classList.add("fr"); 
//     }
//     if (language === "SP") {
//         descriptionElement.classList.add("sp"); 
//     }

//     modalOverlay.style.display = "block";
//     popupModal.style.display = "block";

//     setTimeout(() => {
//         modalOverlay.style.opacity = "1";
//         popupModal.style.opacity = "1";
//         popupModal.style.transform = "translate(-50%, -50%) scale(1)";
//     }, 10);
// }

// function hideModal() {
//     modalOverlay.style.opacity = '0';
//     popupModal.style.opacity = '0';
//     popupModal.style.transform = 'translate(-50%, -50%) scale(0)';
//     setTimeout(() => {
//         modalOverlay.style.display = 'none';
//         popupModal.style.display = 'none';
//     }, 300);
// }













