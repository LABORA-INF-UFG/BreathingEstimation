clear all
close all

% Gera lista de arquivos a serem lidos
fileList = dir('Data/Capturas Definitivas.txt/**/*.mat');

lastID = 'none';
stringID = 'identifier';

% Verifica se Excel está instalado
fprintf('\nBuscando instalação do Microsoft Excel...')
ExcelInstalled = 0;
try
    ExcelInstalled = actxserver('Excel.Application');
end
if (ExcelInstalled ~= 0)
    fprintf(' encontrado!\n')
    ExcelInstalled = 1;
else
    fprintf('não encontrado!\n')
end
fileResultsBackUp = 'Resultados.BackUpB.xlsx';
fileResults = 'Resultados.xlsx';
fileResultsPath = [pwd '\'];
copyfile([fileResultsPath, fileResultsBackUp], [fileResultsPath, fileResults]);

fileID = 0;
for fileListIndex = 1:length(fileList)
    if strcmp(fileList(fileListIndex).folder,pwd)
        continue
    end
    clear lastFileName breathBPMHistory breathBPMHistoryOldPCA
    fileName = fileList(fileListIndex).name;
    filePath = [fileList(fileListIndex).folder '\'];
    [stringID, ~, ~, ~, ~] = fileFetchData(fileName);
    if strcmp(lastID,stringID)
        continue;
    end
    fileID = fileID + 1;
    try
        cellIndex = 0;
        for startDataTime = 1:1:100
            try 
                finishedAnalyzing = 0;
                run slidingEstimateBreathingRateMatFile.m;
                cellIndex = cellIndex + 1;
                processTime = toc;
                if ~finishedAnalyzing 
                    exportCell(:,cellIndex) = {stringID,
                    fileID,
                    fileList(fileListIndex).folder(strfind(fileList(fileListIndex).folder,"\Data\")+6:end-4), %folder Name
                    Fs,
                    antennaMax,
                    dataLength/Fs,
                    30,
                    startDataTime,
                    startDataTime+20,
                    BreathRate,
                    expectedBreathingRate,
                    breathBPMResults, 
                    abs(1-(expectedBreathingRate/median(breathBPMResults)))*100, 
                    breathBPMResultsOldPCA, 
                    abs(1-(expectedBreathingRate/median(breathBPMResultsOldPCA)))*100, 
                    HeartRate,
                    heartBPMResults, 
                    abs(1-(HeartRate/median(heartBPMResults)))*100, 
                    heartBPMResultsPlus, 
                    abs(1-(HeartRate/median(heartBPMResultsPlus)))*100, 
                    maxEnergyOldPCA,
                    maxEnergy,
                    min(antSel),
                    max(antSel),
                    apneaResultsOldPCA,
                    apneaResults,
                    processTime};
                end
            catch ME
                fprintf('==================================================\n');
                fprintf('Erro ao processar %s: %s\n', fileName, ME.identifier);
            end
        end
        xlsappend([fileResultsPath, fileResults],exportCell');
    catch ME
        fprintf('==================================================\n');
        fprintf('Erro ao processar %s: %s\n', fileName, ME.identifier);
    end
    lastID = stringID;
end
