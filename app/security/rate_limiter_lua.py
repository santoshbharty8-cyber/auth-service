SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

-- Remove expired timestamps
redis.call("ZREMRANGEBYSCORE", key, 0, now - window)

-- Current number of requests
local count = redis.call("ZCARD", key)

-- If limit exceeded, return current count
if count >= limit then
    return count
end

-- Add current request timestamp
redis.call("ZADD", key, now, now .. "-" .. math.random())

-- Set key expiration in milliseconds
redis.call("PEXPIRE", key, window)

return count + 1
"""