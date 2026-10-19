import { randomUUID } from 'node:crypto';
import { access } from 'node:fs/promises';
import { normalizeContext } from '@earendil-works/pi-ai';
import { companyConfig, companyModel, companyStream } from './company-provider.mjs';

try {
  const company = process.env.INTERNAL_AI_TRANSPORT === 'company-chat';
  if (company) { await companyConfig(); companyModel(); }
  else {
    for (const name of ['INTERNAL_AI_BASE_URL', 'INTERNAL_AI_MODEL', 'INTERNAL_AI_API_KEY']) {
      if (!process.env[name]) throw new Error(`Set ${name}`);
    }
  }
  await access(new URL('../node_modules/@earendil-works/pi-coding-agent/dist/bundle/cli.js', import.meta.url));
  if (!process.argv.includes('--check-only')) console.log('PASS Pi configuration (values hidden; no network requests)');
  if (!process.argv.includes('--check-only') && process.env.PI_DOCTOR_PROBE === '1') {
    if (!company) throw new Error('PROBE=1 is for company-chat; existing OpenAI transport has separate tests');
    const nonce = randomUUID();
    const context = normalizeContext({
      systemPrompt: 'This is a connectivity test. Call diagnostic_echo with the supplied nonce. Do not answer in plain text.',
      messages: [{ role: 'user', content: 'Call diagnostic_echo with nonce ' + nonce, timestamp: Date.now() }],
      tools: [{ name: 'diagnostic_echo', description: 'Harmless diagnostic; the client will not execute it.',
        parameters: { type: 'object', properties: { nonce: { type: 'string', const: nonce } }, required: ['nonce'], additionalProperties: false } }],
    });
    const answer = await companyStream(companyModel(), context).result();
    if (answer.stopReason === 'error' || answer.stopReason === 'aborted') throw new Error(answer.errorMessage);
    const call = answer.content.find(block => block.type === 'toolCall');
    if (!call || call.name !== 'diagnostic_echo' || call.arguments?.nonce !== nonce) {
      throw new Error('COMPANY_TOOLS_NOT_CONFIRMED');
    }
    console.log('PASS company API returned the diagnostic tool name and nonce; no tool executed');
  }
} catch (error) {
  console.error(/^COMPANY_[A-Z0-9_]+$/.test(error.message) || error.message.startsWith('Set ') ? error.message : 'Pi configuration/probe failed (details hidden)');
  if (error.message === 'COMPANY_TOOLS_NOT_CONFIRMED') console.error('HTTP success or plain text does not prove tool support; no tool was executed. Try the explicit json mode if native tools are unsupported.');
  process.exitCode = 1;
}
