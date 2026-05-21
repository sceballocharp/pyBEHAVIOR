  daqreset;

% Recording Parameters
user_data.frec = 1000;
user_data.fsound  = 192000;
user_data.Bin = 0.1;

% % National Instrument Port IN
user_data.IRFork = 6;
user_data.SoundCopy = 5;
user_data.TTLReward = 'Port2/Line6'; % envoie un TTL reward valves
user_data.TTLtrigsounds = 1;
%user_data.TTLtrigcamera1 = 2; 

% National Instrument Port OUT
user_data.Speaker = 0;
user_data.TTLSoundOut = 'Port0/Line2';

% National Instrument digital output ports
user_data.TTLstartcam1 = 'Port2/Line2'; % camera control
user_data.TTLstartcam2 = 'Port2/Line3';  %fake

% Trigger Type
TriggerType = 'IRFork';

%% National instruments   
daqCard = daqlist;
user_data.DeviceName = daqCard.DeviceID(1);

% First session : get the data
sRec = daq('ni');
sRec.Rate = user_data.frec;
  
IRForkChannel = addinput(sRec, user_data.DeviceName, user_data.IRFork, 'Voltage');
IRForkChannel.TerminalConfig = 'SingleEnded';
SoundChannel = addinput(sRec, user_data.DeviceName, user_data.SoundCopy, 'Voltage');
SoundChannel.TerminalConfig = 'SingleEnded';
TrigsoundChannel= addinput(sRec, user_data.DeviceName, user_data.TTLtrigsounds, 'Voltage');
TrigsoundChannel.TerminalConfig = 'SingleEndedNonReferenced';
% TTLtrigcamera1Channel = addinput(sRec, user_data.DeviceName, user_data.TTLtrigcamera1, 'Voltage');
% TTLtrigcamera1Channel.TerminalConfig = 'SingleEnded';

sRec.ScansAvailableFcnCount =  user_data.Bin * sRec.Rate;

%Second session : send the reward (water valve)
sReward = daq('ni');
di = addoutput(sReward,user_data.DeviceName,user_data.TTLReward,'Digital');

%Third session : play the sounds
sSound = daq('ni');
sSound.Rate = user_data.fsound;
% sound
addoutput(sSound, user_data.DeviceName,user_data.Speaker, 'Voltage');
% sound ttls
addoutput(sSound, user_data.DeviceName,user_data.TTLSoundOut, 'Digital');

%% Fourth session : synchronize
sSynchro = daq('ni');
% camera 1
addoutput(sSynchro,user_data.DeviceName,user_data.TTLstartcam1,'Digital');
% camera 2
addoutput(sSynchro,user_data.DeviceName,user_data.TTLstartcam2,'Digital');
write(sSynchro,[0,0]);

user_data.sRec = sRec;
user_data.sReward = sReward;
user_data.sSound = sSound;
user_data.sSynchro = sSynchro;

app.TriggerTypeDropDown.Value = TriggerType;

