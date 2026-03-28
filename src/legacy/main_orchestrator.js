import 'dotenv/config';
import fs from 'node:fs';
import path from 'node:path';
import { initDb, createRun, updateRun, insertMessage, getMessages, insertTask, updateTaskStatus, insertRetry } from './db.js';
import { buildSlidingWindowContext } from './context.js';
import { createInitialPlan } from './workflow.js';
import { invokeAgent } from './agents.js';
import { withRetry } from './retry.js';
import { logger } from './logger.js';

const __dirname = path.dirname(new URL(import.meta.url).pathname);
const rootDir = path.resolve(__dirname, '..');

function loadJson(relativePath) {
  return JSON.parse(fs.readFileSync(path.join(rootDir, relativePath), 'utf8'));
}

function getGoalFromCli() {
  const index = process.argv.indexOf('--goal');
  if (index !== -1 && process.argv[index + 1]) return process.argv[index + 1];
  return process.env.MISSION_CONTROL_DEFAULT_GOAL || 'Resume pending queue';
}

function shouldRetry(error) {
  const text = String(error?.message || error || '').toLowerCase();
  return text.includes('timeout') || text.includes('rate') || text.includes('429') || text.includes('tool');
}

function normalizeQaResult(result) {
  if (result?.status === 'fail') return 'fail';
  if (result?.status === 'pass') return 'pass';
  return 'pass';
}

async function run() {
  const db = initDb();
  const agentsConfig = loadJson('config/agents.json');
  const orchestratorConfig = loadJson('config/orchestrator.json');
  const maxRetries = Number(process.env.MISSION_CONTROL_MAX_RETRIES || orchestratorConfig.maxRetries || 3);
  const goal = getGoalFromCli();

  const runId = createRun(db, goal);
  logger.info('Run started', { runId, goal });
  insertMessage(db, runId, 'system', 'goal', goal, 'Primary mission goal', 1);

  const initialTask = createInitialPlan(goal);
  insertTask(db, runId, initialTask);

  const supervisor = agentsConfig.agents.find((a) => a.id === 'agent-0');
  const researcher = agentsConfig.agents.find((a) => a.id === 'agent-1');
  const designer = agentsConfig.agents.find((a) => a.id === 'agent-2');
  const developer = agentsConfig.agents.find((a) => a.id === 'agent-3');
  const qa = agentsConfig.agents.find((a) => a.id === 'agent-4');

  try {
    updateRun(db, runId, { current_agent: supervisor.id });
    const planResult = await withRetry(
      () => invokeAgent(supervisor, initialTask, { baseDir: __dirname, contextMessages: [] }),
      {
        retries: maxRetries,
        shouldRetry,
        onRetry: async (error, attempt) => {
          insertRetry(db, runId, initialTask.task_id, supervisor.id, attempt, String(error.message || error));
          logger.warn('Retrying supervisor', { attempt, error: String(error.message || error) });
        }
      }
    );
    insertMessage(db, runId, supervisor.id, 'plan', JSON.stringify(planResult, null, 2), 'Supervisor plan', 1);
    updateTaskStatus(db, initialTask.task_id, 'done');

    const researchTask = {
      ...initialTask,
      from: 'agent-0',
      to: 'agent-1',
      context: {
        ...initialTask.context,
        dependencies: ['supervisor-plan']
      }
    };
    insertTask(db, runId, researchTask);

    updateRun(db, runId, { current_agent: researcher.id });
    const researchContext = buildSlidingWindowContext(getMessages(db, runId), orchestratorConfig.context);
    const researchResult = await withRetry(
      () => invokeAgent(researcher, researchTask, { baseDir: __dirname, contextMessages: researchContext }),
      {
        retries: maxRetries,
        shouldRetry,
        onRetry: async (error, attempt) => {
          insertRetry(db, runId, researchTask.task_id, researcher.id, attempt, String(error.message || error));
          logger.warn('Retrying researcher', { attempt, error: String(error.message || error) });
        }
      }
    );
    insertMessage(db, runId, researcher.id, 'research', JSON.stringify(researchResult, null, 2), 'Research output');
    updateTaskStatus(db, researchTask.task_id, 'done');

    const designTask = {
      ...initialTask,
      from: 'agent-0',
      to: 'agent-2',
      context: {
        ...initialTask.context,
        dependencies: ['supervisor-plan', 'research-output']
      }
    };
    insertTask(db, runId, designTask);
    updateRun(db, runId, { current_agent: designer.id });

    const designContext = buildSlidingWindowContext(getMessages(db, runId), orchestratorConfig.context);
    const designResult = await withRetry(
      () => invokeAgent(designer, designTask, { baseDir: __dirname, contextMessages: designContext }),
      {
        retries: maxRetries,
        shouldRetry,
        onRetry: async (error, attempt) => {
          insertRetry(db, runId, designTask.task_id, designer.id, attempt, String(error.message || error));
          logger.warn('Retrying designer', { attempt, error: String(error.message || error) });
        }
      }
    );
    insertMessage(db, runId, designer.id, 'design_spec', JSON.stringify(designResult, null, 2), 'Designer output');
    updateTaskStatus(db, designTask.task_id, 'done');

    let qaState = 'fail';
    let loopCount = 0;
    let latestBuildResult = null;

    while (qaState !== 'pass' && loopCount < maxRetries) {
      loopCount += 1;

      const buildTask = {
        ...initialTask,
        from: 'agent-0',
        to: 'agent-3',
        context: {
          ...initialTask.context,
          dependencies: ['supervisor-plan', 'research-output', 'design-spec'],
          artifacts: latestBuildResult?.artifacts || []
        },
        deliverable: {
          ...initialTask.deliverable,
          acceptance_criteria: [
            ...initialTask.deliverable.acceptance_criteria,
            'must implement approved design/prototype guidance when present',
            'must address latest QA feedback when present'
          ]
        }
      };
      insertTask(db, runId, buildTask);
      updateRun(db, runId, { current_agent: developer.id, retry_count: loopCount - 1 });

      const buildContext = buildSlidingWindowContext(getMessages(db, runId), orchestratorConfig.context);
      latestBuildResult = await withRetry(
        () => invokeAgent(developer, buildTask, { baseDir: __dirname, contextMessages: buildContext }),
        {
          retries: maxRetries,
          shouldRetry,
          onRetry: async (error, attempt) => {
            insertRetry(db, runId, buildTask.task_id, developer.id, attempt, String(error.message || error));
            logger.warn('Retrying developer', { attempt, error: String(error.message || error) });
          }
        }
      );
      insertMessage(db, runId, developer.id, 'artifact', JSON.stringify(latestBuildResult, null, 2), 'Developer output');
      updateTaskStatus(db, buildTask.task_id, 'done');

      const qaTask = {
        ...buildTask,
        from: 'agent-3',
        to: 'agent-4',
        context: {
          ...buildTask.context,
          dependencies: ['build-output']
        }
      };
      insertTask(db, runId, qaTask);
      updateRun(db, runId, { current_agent: qa.id, retry_count: loopCount - 1 });

      const qaContext = buildSlidingWindowContext(getMessages(db, runId), orchestratorConfig.context);
      const qaResult = await withRetry(
        () => invokeAgent(qa, qaTask, { baseDir: __dirname, contextMessages: qaContext }),
        {
          retries: maxRetries,
          shouldRetry,
          onRetry: async (error, attempt) => {
            insertRetry(db, runId, qaTask.task_id, qa.id, attempt, String(error.message || error));
            logger.warn('Retrying qa', { attempt, error: String(error.message || error) });
          }
        }
      );
      insertMessage(db, runId, qa.id, 'qa_feedback', JSON.stringify(qaResult, null, 2), 'QA result', 1);
      updateTaskStatus(db, qaTask.task_id, 'done');
      qaState = normalizeQaResult(qaResult);

      if (qaState === 'pass') {
        logger.info('QA passed', { runId, loopCount });
        break;
      }

      logger.warn('QA failed, looping back to developer', { runId, loopCount });
    }

    if (qaState !== 'pass') {
      updateRun(db, runId, {
        status: 'needs_human',
        current_agent: 'agent-0',
        last_error: 'QA failed after maximum retries',
        retry_count: maxRetries
      });
      insertMessage(db, runId, 'system', 'fatal_error', 'QA failed after maximum retries. Human intervention required.', 'Escalation required', 1);
      logger.error('Run requires human intervention', { runId });
      return;
    }

    updateRun(db, runId, { status: 'completed', current_agent: 'agent-0' });
    insertMessage(db, runId, 'agent-0', 'final', 'Mission completed successfully.', 'Final status', 1);
    logger.info('Run completed', { runId });
  } catch (error) {
    updateRun(db, runId, {
      status: 'needs_human',
      last_error: String(error.message || error)
    });
    insertMessage(db, runId, 'system', 'fatal_error', String(error.stack || error), 'Unhandled orchestrator error', 1);
    logger.error('Unhandled orchestrator error', { runId, error: String(error.message || error) });
    process.exitCode = 1;
  }
}

run();
