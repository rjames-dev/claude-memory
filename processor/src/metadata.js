/**
 * Metadata Extraction
 * Extracts tags, files, decisions, bugs from conversation
 */

const simpleGit = require('simple-git');
const path = require('path');

/**
 * Extract metadata from conversation
 */
async function extractMetadata(conversation, project_path) {
  const metadata = {
    tags: [],
    files: [],
    decisions: [],
    bugs: [],
    gitHash: null,
    gitBranch: null
  };

  try {
    // Extract from conversation messages
    const allText = conversation.messages
      .map(m => m.content || '')
      .join('\n')
      .toLowerCase();

    // Extract tags based on keywords
    const tagKeywords = {
      'security': ['security', 'vulnerability', 'sql injection', 'xss', 'csrf'],
      'performance': ['performance', 'optimization', 'slow', 'faster', 'cache'],
      'bug-fix': ['bug', 'fix', 'error', 'issue', 'problem'],
      'feature': ['feature', 'implement', 'add', 'new'],
      'refactor': ['refactor', 'cleanup', 'reorganize'],
      'documentation': ['document', 'readme', 'comment'],
      'testing': ['test', 'spec', 'coverage'],
      'database': ['database', 'sql', 'query', 'schema', 'migration'],
      'docker': ['docker', 'container', 'compose'],
      'api': ['api', 'endpoint', 'route', 'rest']
    };

    for (const [tag, keywords] of Object.entries(tagKeywords)) {
      if (keywords.some(keyword => allText.includes(keyword))) {
        metadata.tags.push(tag);
      }
    }

    // Extract file mentions (look for paths and filenames)
    const filePattern = /(?:^|\s)([a-zA-Z0-9_\-./]+\.(js|ts|jsx|tsx|py|md|sql|json|yml|yaml|env|sh|dockerfile))/gi;
    const fileMatches = allText.match(filePattern);
    if (fileMatches) {
      metadata.files = [...new Set(fileMatches.map(f => f.trim()))];
    }

    // Extract key decisions (look for decision-making language)
    const decisionPatterns = [
      /(?:decided to|chose to|implemented|using|will use)\s+([^.!?]+)/gi,
      /(?:approach|solution|strategy):\s*([^.!?]+)/gi
    ];

    for (const pattern of decisionPatterns) {
      const matches = allText.matchAll(pattern);
      for (const match of matches) {
        if (match[1] && match[1].length < 200) {
          metadata.decisions.push(match[1].trim());
        }
      }
    }

    // Extract bug mentions
    const bugPatterns = [
      /(?:fixed|resolved|bug):\s*([^.!?]+)/gi,
      /(?:error|issue):\s*([^.!?]+)/gi
    ];

    for (const pattern of bugPatterns) {
      const matches = allText.matchAll(pattern);
      for (const match of matches) {
        if (match[1] && match[1].length < 200) {
          metadata.bugs.push(match[1].trim());
        }
      }
    }

    // Get git state if project_path is provided
    if (project_path) {
      const workspacePath = process.env.CLAUDE_CODE_ROOT || '';
      const fullPath = path.join(workspacePath, project_path);

      try {
        const git = simpleGit(fullPath);
        const isRepo = await git.checkIsRepo();

        if (isRepo) {
          const log = await git.log({ maxCount: 1 });
          const branch = await git.branch();

          metadata.gitHash = log.latest?.hash || null;
          metadata.gitBranch = branch.current || null;
        }
      } catch (gitError) {
        // Not a git repo or git not available - that's ok
        console.log('Git metadata extraction skipped:', gitError.message);
      }
    }

    // Limit arrays to reasonable sizes
    metadata.tags = metadata.tags.slice(0, 10);
    metadata.files = metadata.files.slice(0, 50);
    metadata.decisions = metadata.decisions.slice(0, 10);
    metadata.bugs = metadata.bugs.slice(0, 10);

    return metadata;

  } catch (error) {
    console.error('Error extracting metadata:', error);
    return metadata; // Return partial metadata
  }
}

module.exports = {
  extractMetadata
};
