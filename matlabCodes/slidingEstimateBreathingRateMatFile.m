% ---- Definição de parâmetros ----
% Número de sinais do PCA
signals = 20;

% Intervalo de frequência onde buscará sinal (Hz)
FminBreath = 0.2;
FmaxBreath = 1;

% Intervalo de frequência onde buscará sinal (Hz)
FminHeart = 50/60;
FmaxHeart = 2;

% Banda máxima da frequência que será usada no filtro para estimar
% respiração (Hz)
maxFreqGap = 0.5;

% Séries da PCA anteriores a esta serão ignoradas:
firstPCA = 2;

% ---- Carregando dados ----
% Selecionando arquivo
fprintf('Importando série do arquivo MAT.');
if ~exist('fileName','VAR')
    % Selecionando arquivo
    [fileName, filePath] = uigetfile ('*.mat');
end
fprintf('\b\b\b\b''%s''.\n', fileName);

% Verifica se o arquivo carregado é o mesmo anterior
newFile = 1;
if exist('lastFileName','var')
	if strcmp(lastFileName,fileName)
		newFile = 0;
	end
end

if newFile
    % Abrindo arquivo de dados
    load([filePath, fileName],'magData','phaseData','antSel');
    CSIr = cell2mat(magData);
    CSIi = cell2mat(phaseData);
    antennaMax = 3;
end

tic
% Extraindo dados do nome do arquivo
[stringID, dataType, Fs, antennaNumber, BreathRate, HeartRate] = fileFetchData(fileName);
dataLength = length(CSIi);

% Calculando taxa de respiração estimada

% Arquivos sem apneia
%expectedBreathingRate = 60*(BreathRate/(dataLength/Fs));

% Arquivos com apneia a partir de 90s
expectedBreathingRate = 60*(BreathRate/90);

% Calculando e desembrulhando a diferença de fase do CSI
if antennaMax > 1
    CSIiDiff = CSIi(:,:,1)-CSIi(:,:,2);
    CSIiDiff = unwrap(CSIiDiff);
else
    CSIiDiff = CSIi(:,:,1);
end

% Recortando sinal em amostra de 20 segundos 
firstSample = round(startDataTime * Fs);
lastSample = round((startDataTime+20) * Fs);
if lastSample > dataLength
    lastSample = dataLength;
end

fprintf('%s: (%d s -> %d s)\n', stringID, startDataTime, startDataTime+20);
CSIm = CSIiDiff(firstSample:lastSample,:);

% Limpando variáveis de execuções anteriores
clear CSImFilt maxCSI minCSI maxCSIthreshold minCSIthreshold CSIclean FClow order a b CSImPCAFull maxIndexResults
clear timeAxisFull windowIndex currentMaxFFT currentMaxFFTindex maxFFTFreq maxIndex freqBreath breathBPMResults
clear analyzedLength

% <--- PCA Basic Processing
% Removendo média do sinal
CSImOld = CSIm - mean(CSIm);
%CSImOld = CSIm;

% Definindo número de amostras analisadas
analyzedLength = length(CSImOld);

% Filtro Hampel
CSImOld = hampel(CSImOld);

% Outlier channel remover
maxCSI = max(CSImOld);
minCSI = min(CSImOld);

% Define limite máximo
maxCSIthreshold = median(maxCSI) + 0.5*(median(maxCSI) - median(minCSI));
% Define limite mínimo
minCSIthreshold = median(minCSI) - 0.5*(median(maxCSI) - median(minCSI));

CSIclean = CSImOld;

% Amostras além dos limites são substituídas pela média das 20 amostras
% mais próximas
for k = 1:size(CSIclean,1)
    for z = 1:size(CSIclean,2)
        if or((CSIclean(k,z) > maxCSIthreshold),(CSIclean(k,z) < minCSIthreshold))
            CSIclean(k,z) = mean(CSIclean(findNearbySamples(CSIclean,k,min([20 size(CSIclean,1)])),z));
        end
    end
end
CSImOld = CSIclean;

% Removendo frequências altas do sinal:
% Filtro passa-baixas butterworth de ordem 2, frequência de corte de 3 Hz
if exist('filterCutoffLowFreq','var')
    FClow = filterCutoffLowFreq;
else
    FClow = 3;
end

order = 2;
[b,a]=butter(order,FClow/(Fs/2),'low');
CSImOld = filtfilt(b, a, CSImOld);
CSImOld = CSImOld - mean(CSImOld);

% Extraindo os 20 componentes principais (PCA)
CSImPCA = pca(CSImOld','NumComponents',20);

% Gerando eixo do tempo
timeAxisFull = [1/Fs:1/Fs:size(CSIm,1)/Fs]';

% Definindo variáveis do intervalo de busca do sinal;
dt = 1/Fs;
T = length(CSImPCA)/Fs;
df = 1/T;
fNQ = 1/dt/2;
fftFreq = (0:df:fNQ);
intervaloMin = find(fftFreq>FminBreath);
intervaloMin = max([1,intervaloMin(1)]);
intervaloMax = find(fftFreq>FmaxBreath);
intervaloMax = max([1,intervaloMax(1)]);

maxFFT = -1000;
maxIndex = 1;
% Buscando picos na FFT das componentes principais 2 e acima (componentes 1
% geralmente dão resultados ruins)
for j=firstPCA:signals
    [fftFreq, fftPCA] = calcFFT(CSImPCA(:,j),Fs);
    % Buscando pico
    [currentMaxFFT currentMaxFFTIndex] = max(fftPCA(intervaloMin:intervaloMax));
    currentMaxFFTIndex = currentMaxFFTIndex + (intervaloMin - 1);
    if maxFFT ~= max([maxFFT;currentMaxFFT]) && (fftFreq(currentMaxFFTIndex) ~= fftFreq(intervaloMin)) && (fftFreq(currentMaxFFTIndex) ~= fftFreq(intervaloMax))
        maxIndex = j;
        maxFFTFreq = fftFreq(currentMaxFFTIndex);
    end
    if (fftFreq(currentMaxFFTIndex) ~= fftFreq(intervaloMin)) && (fftFreq(currentMaxFFTIndex) ~= fftFreq(intervaloMax))
        [maxFFT] = max([maxFFT;currentMaxFFT]);
    end            
end

% Estimando frequência da respiração
[fftFreq, fftPCA] = calcFFT(CSImPCA(:,maxIndex),Fs);
freqBreath = maxFFTFreq;
breathBPMResultsOldPCA = 60/(1/freqBreath);
maxEnergyOldPCA = maxFFT;
% PCA Basic Processing --->

% <---- CardioFi Preprocessing

% Hampel Filter 0.5s window, 0.4* std threshold
CSIm = hampel(CSIm,round(0.5*Fs),0.4);

% Calculate the average variance over C windows, with default windows size.
% The algorithm computes Ev = 1/c * sum(varianceOfWindow(1:c))
varianceThreshold = 1.2;
defaultWindowAmount = 5;
windowDuration = round(3 * Fs);
clear Ev
for subCarrier=1:size(CSIm,2)
    for i=1:defaultWindowAmount
        Ev(i,subCarrier) = var(CSIm(1+(i-1)*windowDuration:i*windowDuration,subCarrier));
    end
end
thresholdEv = mean(Ev)*varianceThreshold;

% Calculate the window sizes that surpasses the variance threshold calculated above.
clear windowEv
fprintf('Preprocessando...\n');
for subCarrier=1:size(CSIm,2)
    windowIndex = 1;
    windowEv(windowIndex,subCarrier) = 1;
    for i=1:length(CSIm)
        EvScan = var(CSIm(windowEv(windowIndex,subCarrier):i,subCarrier));
        if EvScan > thresholdEv(subCarrier)
            windowIndex = windowIndex + 1;
            windowEv(windowIndex,subCarrier) = i;
        end
    end
    windowEv(windowIndex+1,subCarrier) = 0;
end

% Create the trend signal (mean along the windows calculated above).
clear trendDW
trendDW = zeros(size(CSIm));
for subCarrier=1:size(CSIm,2)
    for i=2:size(windowEv,1)
        if windowEv(i,subCarrier) > 0
            trendDW(windowEv(i-1,subCarrier):windowEv(i,subCarrier)-1,subCarrier) = mean(CSIm(windowEv(i-1,subCarrier):windowEv(i,subCarrier)-1,subCarrier));
        else
            trendDW(windowEv(i-1,subCarrier):end,subCarrier) = mean(CSIm(windowEv(i-1,subCarrier):end,subCarrier));
            break;
        end
    end
end

% Hampel Filter 0.5s window, 0.1* std threshold
CSImFilt = hampel(CSIm-trendDW,round(0.5*Fs),0.1);

% CardioFi Preprocessing ---->

% Definindo número de amostras analisadas
analyzedLength = length(CSImFilt);

% Buscando pico de respiração em cada subportadora
carrierIndex = 0;
clear breathBPMResults fftFreq fftAmp
for subCarrier = 1:size(CSImFilt,2)
    carrierIndex = carrierIndex + 1;
    [fftFreq, fftAmp(:,carrierIndex)] = calcFFT(CSImFilt(:,subCarrier),Fs);
    [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminBreath,fftFreq<FmaxBreath),carrierIndex),fftFreq(and(fftFreq>FminBreath,fftFreq<FmaxBreath)));
    [~, freqBreath] = max(freqAmp);
    breathBPMResults(carrierIndex) = freqIndex(freqBreath)*60;
end

maxEnergy = max(freqAmp);
breathBPMResults = median(breathBPMResults); 

% Heart rate estimation:
FminHeart = max(2*breathBPMResults/60,50/60);
FmaxHeart = 2;

% Bandpass filtering between FminHeart and FmaxHeart
order = 1;
[b,a]=butter(order,[FminHeart/(Fs/2) FmaxHeart/(Fs/2)],'bandpass');
CSIm = filtfilt(b, a, CSIm);

% <----- Seleção de subportadoras:

% Split signal in moving window of 20 seconds, step by 1 second
% For each subcarrier, each time window calculate peak frequency R
% between FminHeart and FmaxHeart.
% Calculate psi = 1/(var(R))

windowSize = round(20*Fs);
windowStep = round(1*Fs);
windowIndex = 0;
clear fftFreq fftAmp peakFreq
for subCarrier=1:size(CSIm,2)
    for windowStart=1:windowStep:size(CSIm,1)
        windowIndex = windowIndex + 1;
        if (windowStart+windowSize) < size(CSIm,1)
            [fftFreq, fftAmp] = calcFFT(CSIm(windowStart:windowStart+windowSize,subCarrier),Fs);
            [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminHeart,fftFreq<FmaxHeart)),fftFreq(and(fftFreq>FminHeart,fftFreq<FmaxHeart)));
            [~, maxFreqIndex] = max(freqAmp);
            if ~isempty(freqIndex(maxFreqIndex))
                peakFreq(windowIndex,subCarrier) = freqIndex(maxFreqIndex);
            else
                peakFreq(windowIndex,subCarrier) = 0;
            end
        else
            [fftFreq, fftAmp] = calcFFT(CSIm(windowStart:end,subCarrier),Fs);
            [freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminHeart,fftFreq<FmaxHeart)),fftFreq(and(fftFreq>FminHeart,fftFreq<FmaxHeart)));
            [~, maxFreqIndex] = max(freqAmp);
            if ~isempty(freqIndex(maxFreqIndex))
                peakFreq(windowIndex,subCarrier) = freqIndex(maxFreqIndex);
            else
                peakFreq(windowIndex,subCarrier) = 0;
            end
            windowIndex = 0;
            break;
        end
    end
end

spectralStability = 1./var(peakFreq(:,:));
normSS = normalize(spectralStability,'range',[0,1]);
selectedCarriers = find(normSS>0.2);

if isempty(selectedCarriers)
    [~, selectedCarriers] = max(spectralStability);
end
% Seleção de subportadoras ----->

clear fftFreq fftAmp
carrierIndex = 0;
for subCarrier = selectedCarriers
    carrierIndex = carrierIndex + 1;
    [fftFreq, fftAmp(:,carrierIndex)] = calcFFT(CSImFilt(:,subCarrier),Fs);
end

fftAmp = mean(fftAmp,2);
%fftAmp = fftAmp - hampel(fftAmp,10,0.01);
[freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminHeart,fftFreq<FmaxHeart)),fftFreq(and(fftFreq>FminHeart,fftFreq<FmaxHeart)));
[~, maxFreqIndex] = max(freqAmp);
heartBPMResults = freqIndex(maxFreqIndex)*60;

fftAmp = fftAmp - hampel(fftAmp,10,0.01);
[freqAmp, freqIndex] = findpeaks(fftAmp(and(fftFreq>FminHeart,fftFreq<FmaxHeart)),fftFreq(and(fftFreq>FminHeart,fftFreq<FmaxHeart)));
[~, maxFreqIndex] = max(freqAmp);
heartBPMResultsPlus = freqIndex(maxFreqIndex)*60;

fprintf('Respiração: CardioFi %3.2f, PCA Básico %3.2f (esperado: %3.2f); Coração: CardioFi %3.2f, CardioFi+ %3.2f (esperado: %3.2f)\n', breathBPMResults, breathBPMResultsOldPCA, expectedBreathingRate, heartBPMResults, heartBPMResultsPlus, HeartRate);
lastFileName = fileName;

% Detecção de apneia
apneaMinSamples = 5;
apneaMaxSamples = 10;

if exist('breathBPMHistory','var')
    breathBPMHistory = [breathBPMHistory;breathBPMResults];
else
    breathBPMHistory = breathBPMResults;
end
breathDiff = diff(breathBPMHistory);
if size(breathBPMHistory) < apneaMinSamples
    apneaResults = 'Calibrando';
else
    if isempty(find(breathDiff(end-apneaMaxSamples:end)==0))
        apneaResults = 'Apneia';
    elseif isempty(find(breathDiff(end-apneaMinSamples:end)==0))
        apneaResults = 'Possível Apneia';
    else
        apneaResults = 'Regular';
    end
end

% Detecção de apneia PCA
apneaMinSamples = 5;
apneaMaxSamples = 10;

if exist('breathBPMHistoryOldPCA','var')
    breathBPMHistoryOldPCA = [breathBPMHistoryOldPCA;breathBPMResultsOldPCA];
else
    breathBPMHistoryOldPCA = breathBPMResultsOldPCA;
end
breathDiff = diff(breathBPMHistoryOldPCA);
if size(breathBPMHistoryOldPCA) <= apneaMaxSamples
    apneaResultsOldPCA = 'Calibrando';
else
    if isempty(find(breathDiff(end-apneaMaxSamples:end)==0))
        apneaResultsOldPCA = 'Apneia';
    elseif isempty(find(breathDiff(end-apneaMinSamples:end)==0))
        apneaResultsOldPCA = 'Possível Apneia';
    else
        apneaResultsOldPCA = 'Regular';
    end
end