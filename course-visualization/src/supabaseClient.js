import { createClient } from "@supabase/supabase-js";

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL;

console.log('URL being parsed:', JSON.stringify(supabaseUrl));
console.log('URL length:', supabaseUrl.length);
console.log('URL chars:', supabaseUrl.split('').map(c => c.charCodeAt(0)));

const supabaseKey = process.env.REACT_APP_SUPABASE_KEY;

export const supabase = createClient(supabaseUrl, supabaseKey);
