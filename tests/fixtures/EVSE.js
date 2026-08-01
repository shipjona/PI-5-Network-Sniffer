let EVSE = {
    /* System */
    command: 0,
    ignore: 0,

    gridRange:3,
    
    /* Main data */
    status: 12,
    pilot: 12,
    currentSet: 12,
    voltageAI: 190,
    powerAI: 100,
    aiMode: 0,
    aiModeCurrent: 7,
    phase3Settings: 0,
    phase3Value: 15,
    ground: 0,
    groundCtrl: 1,
    
    /* Meter data */
    voltage1: 0,
    voltage2: 0,
    voltage3: 0,
    current1: 0,
    current2: 0,
    current3: 0,
    power: 0,
    temp1: '-',
    temp2: '-',
    // temp3: '-',
    // temp4: '-',
    sessionPower: 0,
    sessionTime: 0,
    totalPower: 0,
    sessionMoney: 0,
   
    /* timer */


    
    /* wifi */
    WifiMode: '-',
    broadcastMode: '-',
    ssidNameAP: '-',
    ssidPasswordAP: '-',
    ssidPasswordAPConf: '-',
    ssidName: '-',
    ssidPassword: '-',
    ssidPasswordConf: '-',
    httpUsername: "",
    httpPassword: "",
    httpPasswordConf:"",
    localIP: '',
    ESP_MAC: '',
    STA_MAC: '-',
    mac_bind: '-',

    /* admin */
    evseType: 1,
    evseTypeRelay: '-',
    evseDesignCurrent: 80,
    evseMinCurrent: 7,
    evseVoltageC1: '-',
    evseVoltageC2: '-',
    evseVoltageC3: '-',
    evseCurrentC1: '-',
    evseCurrentC2: '-',
    evseCurrentC3: '-',
    evseFreqCPC: '-',
    
    /* limits */
    evseEnabled: 0,
    timeLimit: 0,
    energyLimit: 0,
    moneyLimit:0,
    
    /* rates */
    tarif_1: 0,
    tarif_A: 0,
    tarif_B: 0,

    /* Schedule_1 */
    sh1Enabled:0, 
    sh1Start: "00:00",
    sh1Stop: "23:59",
    sh1CurrentEnable: 0,
    sh1CurrentValue: 0,
    sh1EnergyEnable:0,
    sh1EnergyValue: 0,
    
    /* Schedule_2 */
    sh2Enabled:0, 
    sh2Start: "00:00",
    sh2Stop: "23:59",
    sh2CurrentEnable:0,
    sh2CurrentValue: 0,
    sh2EnergyEnable: 0,
    sh2EnergyValue: 0,
    /* Time */
    timeZone: 0,
    prevTimeZone: 255,
    systemTime: 0,
    
    /* Other */
    limitsStatus: 0,
    timeLimitS:0,
    energyLimitS:0,
    moneyLimitS:0,

    adapter: 0,

    /* Security control */ 
    security_ctrl:0,
    
    /* Version */ 
    versionFW: 0,
    randomKey: 0,

    /* Statistics */
    session_money:0,
    IEM_1_money:0,
    IEM_2_money:0,

    oneCharge:0,
    tmp_ctrl:0,
    language:0xDD,

    /* RAW data */
    cp_p: 0,
    cp_d: 0,
    v1_f_raw: 0,
    v1_raw: 0,
    v2_raw: 0,
    v3_raw: 0,
    c1_raw: 0,
    c2_raw: 0,
    c3_raw: 0,
    cl_h_raw: 0,
    cl_l_raw: 0,
    t1_raw: '-',
    t2_raw: '-',
    vb_raw: 0,
    /* admin */

    evType: 1,
    rlType: 0,
    evseDesignCurrentC: 80,
    Cmax:0,
    Cmin: 7,

    kV1: 0,
    kV2: 0,
    kV3: 0,
    kC1: 0,
    kC2: 0,
    kC3: 0,
    kCL: 0,

    add_current:0,
    led_ctrl:0,
    one_charge:0,
    tmp_ctrl:0,
    tmp_ctrl_val:0,

    urlProtocol:"",
    urlUrl:"",
    urlPort:"",
    urlPath:"",
    resProviderURL:"",
    Connectors:[],
    stationSN:"",

    /*OCPP*/
    ocppVendor:0,
    ocppConnected:null,
    statusOCPP:null,

    // switchState:0,

};
