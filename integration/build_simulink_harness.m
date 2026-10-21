function build_simulink_harness()
% Integration preparation; requires licensed Simulink and a configured C compiler.
% C Caller exercises the stateless inference core. Feature delay, guard and
% diagnostic state must be integrated separately using the documented interface.
root = fileparts(fileparts(mfilename('fullpath')));
inc = fullfile(root,'embedded');
mdl = 'EngineGuardInference';
if bdIsLoaded(mdl), close_system(mdl,0); end
new_system(mdl); open_system(mdl);
set_param(mdl,'SolverType','Fixed-step','Solver','FixedStepDiscrete','FixedStep','0.05');
set_param(mdl,'SimCustomHeaderCode','#include "engine_guard.h"', ...
    'SimCustomInclude',inc,'SimCustomSources',fullfile(inc,'engine_guard.c'));
set_param(mdl,'CustomHeaderCode','#include "engine_guard.h"', ...
    'CustomInclude',inc,'CustomSource',fullfile(inc,'engine_guard.c'));
% Six current inputs, six previous inputs, mass-flow*T/omega. Never include ypim.
u = single([0.01 150 105000 10 300 0.5 0.01 150 105000 10 300 0.5 0.02]);
assignin('base','eg_features',u);
add_block('simulink/Sources/Constant',[mdl '/Features'], ...
    'Value','eg_features','OutDataTypeStr','single','Position',[40 70 140 110]);
add_block('simulink/User-Defined Functions/C Caller',[mdl '/C inference'], ...
    'FunctionName','eg_predict','Position',[210 60 370 120]);
spec = get_param([mdl '/C inference'],'FunctionPortSpecification');
spec.InputArguments(1).Size = '13';
add_block('simulink/Sinks/Out1',[mdl '/Pressure_Pa'],'Position',[440 80 470 100]);
add_line(mdl,'Features/1','C inference/1');add_line(mdl,'C inference/1','Pressure_Pa/1');
save_system(mdl,fullfile(root,'build',[mdl '.slx']));
fprintf('Harness created. Run update/simulation and compare against golden vectors.\n');
end
