OTP_VERIFY_LUA = """
local otp_key = KEYS[1]
local attempts_key = KEYS[2]

local provided_otp = ARGV[1]
local max_attempts = tonumber(ARGV[2])

-- get stored OTP
local stored_otp = redis.call("GET", otp_key)

if not stored_otp then
    return -1
end

-- check attempts
local attempts = redis.call("GET", attempts_key)

if attempts and tonumber(attempts) >= max_attempts then
    return -2
end

-- compare OTP
if stored_otp ~= provided_otp then
    redis.call("INCR", attempts_key)
    return 0
end

-- correct OTP → delete keys
redis.call("DEL", otp_key)
redis.call("DEL", attempts_key)

return 1
"""