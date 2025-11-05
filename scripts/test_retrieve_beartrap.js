(async () => {
  try {
    // load env and internals
    require('dotenv').config();
    const ask = require('../ask.js');
    const intern = ask._internal;

    console.log('Forcing reindex and Chroma usage (CHROMA_ENABLED=', process.env.CHROMA_ENABLED, ')');
    await intern.indexKnowledgeBase({ forceReindex: true });

    console.log('Retrieving top 5 for "bear trap"...');
    const res = await intern.retrieveRelevant('bear trap', 5);
    console.log('Results:', JSON.stringify(res, null, 2));
  } catch (err) {
    console.error('Test failed:', err);
    process.exit(1);
  }
})();
