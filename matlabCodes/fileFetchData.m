function [stringID, dataType, Hz, antennaNumber, BreathRate, HeartRate] = fileFetchData(fileName)
%   Extrai dados do nome do arquivo cujo formato remete aos seguinte:
%   <identificador>-<amplitude_ou_fase>-<taxa_de_amostragem>Hz-ant<numero_da_antena>-<ciclos_do_sinal_vital>R.csv
%
%   Exemplos: 
%    Coleta com identificador “levePi80cmCostasMiLucas1�?, dados de 
%    amplitude, dados da antena 1, com taxa de amostragem de 20,59Hz, 
%    onde um total de 15 ciclos de respiração foram capturados:
%      'levePi80cmCostasMiLucas1-amp-ant1-20_59Hz-15R.csv'
%
%    Coleta com identificador “levePi80cmFrenteFresnelLucas1�?, dados 
%    de fase, dados da antena 2, com taxa de amostragem de 19,98Hz, 
%    onde um total de 15,5 ciclos de respiração foram capturados:
%       'levePi80cmFrenteFresnelLucas1-phase-ant2-19_98Hz-15_5R.csv'
%
%   Sintaxe:
%   [identificador, amplitude_ou_fase, taxa_de_amostragem, numero_da_antena, ciclos_do_sinal_vital] = fileFetchData(nome_do_arquivo)

indexHz(2) = strfind(fileName,'Hz');
indexTempA = find(strfind(fileName,'-')<indexHz(2));
indexTempB = strfind(fileName,'-');
indexHz(1) = indexTempB(indexTempA(end));
stringHz = strrep(fileName(indexHz(1)+1:indexHz(2)-1),'_','.');
Hz = str2num(stringHz);

minIndex = indexHz(1)-1;

if ~contains(fileName,'-phase')
    dataType = 'amp';
    minIndex = min([strfind(fileName,'-amp')-1 minIndex]);
else
    dataType = 'phase';
    minIndex = min([strfind(fileName,'-phase')-1 minIndex]);
end

if contains(fileName,'ant')
    indexAnt(1) = strfind(fileName,'-ant')+4;
    indexTempA = find(strfind(fileName,'-')>indexAnt(1));
    indexTempB = strfind(fileName,'-');
    indexAnt(2) = indexTempB(indexTempA(1));
    antennaNumber = str2num(fileName(indexAnt(1):indexAnt(2)-1));
    minIndex = min([indexAnt(1)-1 minIndex]);
else
    antennaNumber = 1;
end


if contains(fileName,'R','IgnoreCase',false)
    fileNameTemp = fileName(minIndex:end);
    indexRate(2) = strfind(fileNameTemp,'R');
    indexTempA = find(strfind(fileNameTemp,'-')<indexRate(2));
    indexTempB = strfind(fileNameTemp,'-');
    indexRate(1) = indexTempB(indexTempA(end));
    stringRate = strrep(fileNameTemp(indexRate(1)+1:indexRate(2)-1),'_','.');
    BreathRate = str2num(stringRate);
    minIndex = min([indexRate(1)-1+minIndex minIndex]);
else
    BreathRate = 0;
end

if contains(fileName,'bpm','IgnoreCase',false)
    fileNameTemp = fileName(minIndex:end);
    indexRate(2) = strfind(fileNameTemp,'bpm');
    indexTempA = find(strfind(fileNameTemp,'-')<indexRate(2));
    indexTempB = strfind(fileNameTemp,'-');
    indexRate(1) = indexTempB(indexTempA(end));
    stringRate = strrep(fileNameTemp(indexRate(1)+1:indexRate(2)-1),'_','.');
    HeartRate = str2num(stringRate);
    minIndex = min([indexRate(1)-1+minIndex minIndex]);
else
    HeartRate = 0;
end

indexID = [1 minIndex];
stringID = fileName(indexID(1):indexID(2));


end
