import fs from 'fs';
import { GoogleGenerativeAI } from '@google/generative-ai';

// Configuration
const INPUT_FILE = 'bulk_content.json';
const OUTPUT_FILE = 'bulk_content.json';
const GEMINI_API_KEY = process.env.GEMINI_API_KEY || '';

const PINTEREST_PROMPT = `You are a Pinterest Growth Editor. Generate optimized pin content.

RULES:
- Title: ≤100 chars, keyword-front, no leading emoji
- Description: ≤500 chars, start with 40-55 word direct answer, include common names naturally, end with hashtags and sources
- Alt text: 80-140 chars, literal visual description
- 5-6 hashtags: mix of broad (#GardeningTips #PlantCare #GrowYourOwn) and niche
- If health claims: add caution + cite org names (USDA, NIH, FDA, RHS)
- NO URLs in description
- Voice: cozy_authority (allow 1 micro-story ≤120 chars after direct answer)

INPUT:
Topic: {TOPIC}
Product URL: {URL}

OUTPUT JSON:
{
  "pin_title": "...",
  "pin_description": "...",
  "alt_text": "...",
  "hashtags": ["#tag1", "#tag2", ...]
}`;

async function generateContent() {
  if (!GEMINI_API_KEY) {
    console.error('❌ GEMINI_API_KEY not set!');
    console.log('Set it with: $env:GEMINI_API_KEY="your-key"');
    process.exit(1);
  }

  const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);
  const model = genAI.getGenerativeModel({ model: 'gemini-1.5-flash' });

  // Load pins
  const pins = JSON.parse(fs.readFileSync(INPUT_FILE, 'utf-8'));
  console.log(`📌 Loaded ${pins.length} pins`);

  // Filter pins with 0 clicks that need content
  const toProcess = pins.filter(p =>
    p.analytics?.clicks === 0 &&
    (!p.content || !p.content.pin_title)
  );

  console.log(`🎯 Processing ${toProcess.length} pins with 0 clicks`);

  let processed = 0;
  let errors = 0;

  for (const pin of toProcess) {
    const idx = pins.findIndex(p => p.pinId === pin.pinId);
    console.log(`\n[${processed + 1}/${toProcess.length}] ${pin.title?.slice(0, 50) || pin.pinUrl}`);

    try {
      const topic = pin.title?.replace('This may contain:', '').trim() ||
                   pin.destUrl?.split('/').pop()?.replace(/-/g, ' ') ||
                   'Unknown product';

      const prompt = PINTEREST_PROMPT
        .replace('{TOPIC}', topic)
        .replace('{URL}', pin.destUrl || '');

      const result = await model.generateContent(prompt);
      const text = result.response.text();

      // Parse JSON from response
      const jsonMatch = text.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        const content = JSON.parse(jsonMatch[0]);
        pins[idx].content = content;
        console.log(`  ✓ Generated: ${content.pin_title?.slice(0, 50)}...`);
      } else {
        throw new Error('No JSON in response');
      }

      processed++;

      // Save progress every 10 pins
      if (processed % 10 === 0) {
        fs.writeFileSync(OUTPUT_FILE, JSON.stringify(pins, null, 2));
        console.log(`  💾 Progress saved (${processed}/${toProcess.length})`);
      }

      // Rate limiting
      await new Promise(r => setTimeout(r, 1000));

    } catch (err) {
      console.log(`  ✗ Error: ${err.message}`);
      errors++;
    }
  }

  // Final save
  fs.writeFileSync(OUTPUT_FILE, JSON.stringify(pins, null, 2));
  console.log(`\n✅ Done! Processed: ${processed}, Errors: ${errors}`);
  console.log(`📄 Saved to ${OUTPUT_FILE}`);
}

generateContent();
