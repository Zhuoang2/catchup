// Sample data for the CatchUp UI prototypes. Content comes from the manual test of
// add-podcast-and-video-sources (2026-10-05); the English digest is a translation for layout checks.
window.SAMPLE = {
  run: {
    collecting: {
      status: 'collecting', sources_total: 5, items_total: 0, items_done: 0,
      checks: [
        { title: 'The Daily', status: 'no_new_items' },
        { title: 'How to Start a Podcast', status: 'new_items' },
      ],
    },
    summarizing: {
      status: 'summarizing', sources_total: 5, items_total: 12, items_done: 5,
      checks: [
        { title: 'The Daily', status: 'no_new_items' },
        { title: 'How to Start a Podcast', status: 'new_items' },
        { title: 'Google for Developers', status: 'failed', error: 'The source could not be fetched.' },
        { title: 'Astral Codex Ten', status: 'new_items', possible_gap: true },
        { title: 'Simon Willison’s Weblog', status: 'new_items' },
      ],
    },
    succeeded: {
      status: 'succeeded', sources_total: 5, items_total: 12, items_done: 12,
      waiting: 5, deferred: 2, tokens: [8663, 1893],
      checks: [
        { title: 'The Daily', status: 'no_new_items' },
        { title: 'How to Start a Podcast', status: 'new_items' },
        { title: 'Google for Developers', status: 'rate_limited' },
        { title: 'Astral Codex Ten', status: 'new_items' },
        { title: 'Simon Willison’s Weblog', status: 'new_items' },
      ],
    },
    none: {
      status: 'no_new_content', sources_total: 5, items_total: 0, items_done: 0,
      waiting: 5, deferred: 0, tokens: [0, 0],
      checks: [
        { title: 'The Daily', status: 'no_new_items' },
        { title: 'How to Start a Podcast', status: 'no_new_items' },
        { title: 'Google for Developers', status: 'failed', error: 'The source could not be fetched.' },
        { title: 'Astral Codex Ten', status: 'no_new_items' },
        { title: 'Simon Willison’s Weblog', status: 'no_new_items' },
      ],
    },
    failed: {
      status: 'failed', sources_total: 5, items_total: 12, items_done: 3, tokens: [1240, 310],
      error: 'The provider rejected the API key. Check the model settings.',
      checks: [
        { title: 'The Daily', status: 'no_new_items' },
        { title: 'How to Start a Podcast', status: 'new_items' },
      ],
    },
  },
  lastDigest: { id: 3, created: '2026-10-05T22:23:58', items: 1, sources: 1 },

  digests: {
    zh: {
      id: 1, lang: 'zh-Hans', created: '2026-10-05T19:48:34', model: 'deepseek-flash', tokens: [8663, 1893], items: 4, sources: 3, waitDays: 7,
      topics: [
        {
          title: '播客脱颖而出的制作与定位策略',
          overview: '围绕如何让播客节目脱颖而出，强调先明确听众、信息与视角，再用“十个词描述”聚焦定位，并结合内容打磨、社区联动、低成本推广和务实预期来实现可持续成功。',
          items: [{
            title: 'The Key to Making Your Podcast Stand Out // Eric Nuzum',
            source: 'How to Start a Podcast', kind: 'podcast', published: '2026-10-01T09:00:00',
            summary: '本期节目由 Travis Albritton 与播客制作人 Eric 对谈，围绕如何让播客脱颖而出，以及新书《Make Noise》的创作背景展开。Eric 结合在 NPR、Audible 和 Magnificent Noise 的经验，强调先理解听众、明确信息与视角，再考虑形式和资源。',
            points: [
              '出书动机：播客行业已成熟，新节目激增，很多创作者面临的障碍相似；本书聚焦如何把内容做好，而非设备购买或变现技巧。',
              '十个词描述：具体定义听众、要带他们经历的旅程、你想说的话、你的身份/视角和期望结果。',
              '成功与预期：先定义听众，才能定义成功；不要因没有赞助或巨大下载量而过早放弃。',
              '推广与采访：最好的营销是让下一集比上一集更好；采访要真诚好奇，后期像讲故事一样剪辑。',
            ],
          }],
        },
        {
          title: '利用 Gemini 将语音转化为实体打印纪念物',
          overview: '介绍 Journal Receipts 项目：一盏可对话的灯，使用 Gemini 分析说话中的情绪、语气和氛围，再由 Nano Banana 生成象征性图案，并打印成可触摸的收据式纪念物。',
          items: [{
            title: 'How to transform audio into physical prints using Gemini and Google AI Studio',
            source: 'Google for Developers', kind: 'youtube', published: '2026-10-01T12:00:13',
            summary: '该项目名为 Journal Receipts，是一盏可以与之对话的灯。它利用 Gemini 分析说话中的情绪、语气和氛围，再将结果交给 Nano Banana 生成象征性图案，并打印成可触摸的收据式纪念物。',
          }],
        },
        {
          title: '社区与写作',
          overview: '（占位）用于展示普通文章摘要和“摘要不可用”状态的示例主题。',
          items: [
            {
              title: '(a weekly open thread — placeholder title)', source: 'Astral Codex Ten', kind: 'feed', published: '2026-10-05T03:10:00',
              summary: '（占位摘要）每周开放讨论帖，列出本周的读者活动安排，并更正上周文章中的一处数据。',
            },
            {
              title: '(an essay whose summary failed — placeholder title)', source: 'Astral Codex Ten', kind: 'feed',
              published: '2026-10-04T18:20:00', unavailable: true,
            },
          ],
        },
      ],
      creator: [
        { source: 'Google for Developers', kind: 'youtube', items: [
          { title: 'Gemma 4 12B: The encoder-free model explained', published: '2026-09-30T23:00:10', reason: 'captions_off' },
        ] },
        { source: 'The Daily', kind: 'podcast', items: [
          { title: '(an episode title)', published: '2026-09-28T10:00:00', reason: 'no_transcript' },
        ] },
      ],
    },
    en: {
      id: 1, lang: 'en', created: '2026-10-05T19:48:34', model: 'deepseek-flash', tokens: [8102, 1764], items: 2, sources: 2, waitDays: 7,
      topics: [
        {
          title: 'How podcasts stand out: positioning and craft',
          overview: 'Know your listener, your message, and your point of view first; use a "ten-word description" to focus the show, then improve each episode, work with communities, and keep expectations realistic.',
          items: [{
            title: 'The Key to Making Your Podcast Stand Out // Eric Nuzum',
            source: 'How to Start a Podcast', kind: 'podcast', published: '2026-10-01T09:00:00',
            summary: 'Travis Albritton talks with producer Eric Nuzum about making a podcast stand out and the background of his book Make Noise. Drawing on NPR, Audible, and Magnificent Noise, Eric argues for understanding the audience, message, and perspective before format and resources.',
            points: [
              'Why the book: the industry has matured and new shows share the same obstacles; the book is about making content good, not gear or monetization.',
              'Ten-word description: define the listener, the journey, what you want to say, who you are, and the intended result.',
              'Success: define your audience before defining success; do not quit early for lack of sponsors or downloads.',
              'Promotion and interviews: the best marketing is a better next episode; be genuinely curious and edit like a storyteller.',
            ],
          }],
        },
        {
          title: 'Turning speech into printed keepsakes with Gemini',
          overview: 'Journal Receipts is a lamp you talk to: Gemini reads mood and tone from your voice, Nano Banana turns it into a symbolic image, and a small printer makes a receipt-sized keepsake.',
          items: [{
            title: 'How to transform audio into physical prints using Gemini and Google AI Studio',
            source: 'Google for Developers', kind: 'youtube', published: '2026-10-01T12:00:13',
            summary: 'Journal Receipts is a lamp you can talk to. Gemini analyzes the emotion, tone, and atmosphere of what you say, Nano Banana creates a symbolic pattern, and the result is printed as a receipt-style keepsake.',
          }],
        },
      ],
      creator: [],
    },
    creatorOnly: {
      id: 2, lang: 'zh-Hans', created: '2026-10-05T20:31:02', model: 'deepseek-flash', tokens: [0, 0], items: 1, sources: 1, waitDays: 7,
      topics: [],
      creator: [
        { source: 'Google for Developers', kind: 'youtube', items: [
          { title: 'How to transform audio into physical prints using Gemini and Google AI Studio', published: '2026-10-01T12:00:13', reason: 'captions_off' },
        ] },
      ],
    },
  },

  sources: [
    { title: 'The Daily', kind: 'podcast', feed: 'https://feeds.simplecast.com/Sl5CSM3S', status: 'no_new_items', checked: '2026-10-05T22:23:40' },
    { title: 'How to Start a Podcast', kind: 'podcast', feed: 'https://rss.buzzsprout.com/1.rss', status: 'new_items', checked: '2026-10-05T22:23:41' },
    { title: 'Google for Developers', kind: 'youtube', feed: 'https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw', status: 'failed', checked: '2026-10-05T22:23:44', rate_limited: false },
    { title: 'Astral Codex Ten', kind: 'feed', feed: 'https://www.astralcodexten.com/feed', status: 'new_items', checked: '2026-10-05T22:23:45', possible_gap: true },
    { title: 'Simon Willison’s Weblog', kind: 'feed', feed: 'https://simonwillison.net/atom/everything/', status: null, checked: null },
  ],
  previews: {
    podcast: {
      title: 'The Daily', kind: 'podcast', feed: 'https://feeds.simplecast.com/Sl5CSM3S', site: 'https://www.nytimes.com/the-daily',
      notice: 'show',
      entries: [
        { title: '(episode title 1)', published: '2026-10-05T12:00:00' }, { title: '(episode title 2)', published: '2026-10-04T12:00:00' },
        { title: '(episode title 3)', published: '2026-10-03T12:00:00' }, { title: '(episode title 4)', published: '2026-10-02T12:00:00' },
        { title: '(episode title 5)', published: '2026-10-01T12:00:00' },
      ],
    },
    youtube: {
      title: 'Google for Developers', kind: 'youtube', captions: false,
      feed: 'https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw', site: 'https://www.youtube.com/channel/UC_x5XG1OV2P6uZZ5FSM9Ttw',
      entries: [
        { title: 'How to transform audio into physical prints using Gemini and Google AI Studio', published: '2026-10-01T12:00:00' },
        { title: 'Per-Layer Embeddings (PLE) in Gemma 4 explained', published: '2026-09-25T12:00:00' },
        { title: 'The next generation of voice AI with Google DeepMind', published: '2026-09-24T12:00:00' },
        { title: 'Gemma 4 12B: The encoder-free model explained', published: '2026-09-22T12:00:00' },
      ],
    },
  },
  history: [
    { id: 3, created: '2026-10-05T22:23:58', items: 1, sources: 1, topics: ['利用 Gemini 将语音转化为实体打印纪念物'] },
    { id: 2, created: '2026-10-05T20:31:02', items: 1, sources: 1, topics: ['Creator updates only'] },
    { id: 1, created: '2026-10-05T19:48:34', items: 4, sources: 3, topics: ['播客脱颖而出的制作与定位策略', '利用 Gemini 将语音转化为实体打印纪念物', '社区与写作'] },
  ],
  models: ['deepseek-flash', 'deepseek-v4-pro'],
}
