const vscode = require('vscode');

function activate(context) {
  const factory = {
    createDebugAdapterDescriptor(session) {
      const python = session.configuration.pythonPath || 'python';
      return new vscode.DebugAdapterExecutable(python, ['-u', '-m', 'debug_adapter']);
    },
  };
  context.subscriptions.push(
    vscode.debug.registerDebugAdapterDescriptorFactory('advpl-testlab', factory)
  );
}

function deactivate() {}

module.exports = { activate, deactivate };
