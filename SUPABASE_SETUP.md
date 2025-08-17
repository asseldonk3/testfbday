# 🚀 Supabase Setup Guide for Trading System

## Step 1: Create Supabase Account

1. Go to [https://supabase.com](https://supabase.com)
2. Click "Start your project"
3. Sign up with GitHub (recommended) or email
4. **No credit card required!**

## Step 2: Create New Project

1. Click "New Project"
2. Enter project details:
   - **Name**: `trading-system` (or your choice)
   - **Database Password**: Save this securely!
   - **Region**: Choose closest to you
   - **Pricing Plan**: Free tier (default)
3. Click "Create new project"
4. Wait 1-2 minutes for setup

## Step 3: Get Your API Keys

Once project is created:
1. Go to **Settings** (gear icon) → **API**
2. Copy these values:
   - **Project URL**: `https://xxxxx.supabase.co`
   - **Anon/Public Key**: `eyJhbGc...` (long string)
   - Save both for Vercel!

## Step 4: Setup Database Tables

1. Go to **SQL Editor** (left sidebar)
2. Click "New Query"
3. Copy entire contents of `supabase_setup.sql`
4. Paste and click "Run"
5. You should see "Success" messages

## Step 5: Add to Vercel Environment

1. Go to your [Vercel Dashboard](https://vercel.com)
2. Select your project
3. Go to **Settings** → **Environment Variables**
4. Add these variables:
   ```
   SUPABASE_URL = [your-project-url]
   SUPABASE_ANON_KEY = [your-anon-key]
   ```
5. Click "Save" for each

## Step 6: Update Your API

Replace `/api/weekly_candidates` with `/api/weekly_candidates_supabase` in your code to use the database-connected version.

## Step 7: Test It!

1. Visit your Vercel app
2. Click "Select Weekly Candidates"
3. Check Supabase dashboard → **Table Editor** → `watchlist`
4. You should see your selected stocks!

## 📊 Viewing Your Data in Supabase

### Table Editor
- Go to **Table Editor** in left sidebar
- Select any table to view/edit data
- You can filter, sort, and export

### SQL Queries
Quick queries to try in SQL Editor:

```sql
-- View current week's watchlist
SELECT * FROM active_watchlist;

-- View all signals from today
SELECT * FROM recent_signals;

-- Check trading performance
SELECT * FROM portfolio ORDER BY date DESC;

-- Get high-impact news
SELECT * FROM news_items 
WHERE impact_score > 0.7 
ORDER BY published_at DESC;
```

## 🔄 Real-time Subscriptions

Supabase supports real-time updates! Your app can subscribe to changes:

```javascript
// Example: Subscribe to new signals
const subscription = supabase
  .from('signals')
  .on('INSERT', payload => {
    console.log('New signal!', payload.new)
  })
  .subscribe()
```

## 🛡️ Security Notes

- The `anon` key is safe to use in frontend (it's public)
- Row Level Security (RLS) protects your data
- Never expose your `service_role` key (if you have one)
- Database password is only for direct connections

## 🎯 Next Steps

1. **Set up Cron Jobs**: Use Vercel Cron or GitHub Actions to run weekly selection automatically
2. **Add Authentication**: Supabase Auth for user logins
3. **Enable Realtime**: Subscribe to trade signals in your frontend
4. **Add Edge Functions**: For complex trading logic

## 🆘 Troubleshooting

### "Project is paused"
- Free tier pauses after 1 week of inactivity
- Just click "Restore" in dashboard

### "Rate limit exceeded"
- Free tier has rate limits
- Wait a few minutes or upgrade

### "Connection failed"
- Check your environment variables
- Ensure URL starts with `https://`
- Verify API key is complete

## 📈 Free Tier Limits

- ✅ 500 MB database
- ✅ Unlimited API requests (with rate limits)
- ✅ 2 GB bandwidth
- ✅ 50,000 monthly active users
- ✅ 500,000 edge function invocations

Perfect for testing and small-scale trading!

---

Ready to trade! 🚀 Your system now has a full cloud database.