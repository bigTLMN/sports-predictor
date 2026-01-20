import { createClient } from '@supabase/supabase-js'

// 使用 ! 驚嘆號，告訴 TypeScript "這兩個變數一定有值，請放心"
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_KEY!

export const supabase = createClient(supabaseUrl, supabaseKey)