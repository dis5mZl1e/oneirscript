-- Oneirscript private window atmosphere. No user-global settings or game input rewrites.
return function(wezterm, config, assets)
  local states = {}
  local modes = { 'dream', 'clear', 'static' }
  local names = { dream = '梦境氛围 / Dream', clear = '清晰阅读 / Clear', static = '静态 / Still' }
  local palettes = {
    indigo = { label = '靛青梦雾 / Indigo', colors = { '#151326', '#10242c' }, glow = '#759bad', hue = 1.0 },
    moss = { label = '苔绿余光 / Moss', colors = { '#10231c', '#20261c' }, glow = '#83a68b', hue = 0.72 },
    ember = { label = '余烬薄暮 / Ember', colors = { '#291a20', '#201d30' }, glow = '#b7939d', hue = 1.38 },
  }

  local function copy(table)
    local result = {}
    for key, value in pairs(table or {}) do result[key] = value end
    return result
  end

  local function clock()
    local now = wezterm.time.now()
    return tonumber(now:format('%s')) + tonumber(now:format('%f')) / 1000000000
  end

  local function state(window)
    local id = window:window_id()
    if not states[id] then
      local saved = (wezterm.GLOBAL.dreamstrata_window_effects or {})[tostring(id)] or {}
      states[id] = { mode = names[saved.mode] and saved.mode or 'dream',
        palette = palettes[saved.palette] and saved.palette or 'indigo', focus = 1, target = 1,
        pulse = 0, last = clock(), generation = (saved.generation or 0) + 1,
        scheduled = false, initialized = false }
      local preferences = wezterm.GLOBAL.dreamstrata_window_effects or {}
      preferences[tostring(id)] = { mode = states[id].mode, palette = states[id].palette,
        generation = states[id].generation }
      wezterm.GLOBAL.dreamstrata_window_effects = preferences
    end
    return states[id]
  end

  local function remember(window, s)
    local saved = wezterm.GLOBAL.dreamstrata_window_effects or {}
    saved[tostring(window:window_id())] = { mode = s.mode, palette = s.palette, generation = s.generation }
    wezterm.GLOBAL.dreamstrata_window_effects = saved
  end

  local function layers(s)
    local palette = palettes[s.palette]
    local result = {
      { source = { Color = '#101018' }, width = '100%', height = '100%' },
    }
    if s.mode == 'clear' then return result end
    result[#result + 1] = {
      source = { File = assets .. '/still.png' },
      -- One viewport-sized texture avoids dark atlas edges at mirrored seams.
      width = '100%', height = '100%', repeat_x = 'NoRepeat', repeat_y = 'NoRepeat', opacity = 0.65,
      hsb = { hue = palette.hue, saturation = 0.7, brightness = 0.65 },
    }
    if s.mode == 'static' then
      return result
    end
    result[#result + 1] = {
      source = { File = { path = assets .. '/mist.png', speed = 0.45 } },
      width = '100%', height = '100%', repeat_x = 'NoRepeat', repeat_y = 'NoRepeat',
      horizontal_align = 'Center', vertical_align = 'Middle',
      opacity = 0.30 * s.focus + 0.05 * s.pulse,
      hsb = { hue = palette.hue, saturation = 0.7, brightness = 0.65 },
    }
    result[#result + 1] = {
      source = { File = { path = assets .. '/ribbons.png', speed = 0.30 } },
      width = '100%', height = '100%', repeat_x = 'NoRepeat', repeat_y = 'NoRepeat', horizontal_align = 'Center',
      opacity = 0.20 * s.focus, hsb = { hue = palette.hue, saturation = 0.55, brightness = 0.8 },
    }
    if s.pulse > 0.001 then
      result[#result + 1] = { source = { Color = palette.glow },
        width = '100%', height = '100%', opacity = 0.075 * s.pulse }
    end
    return result
  end

  local function frame(existing, s)
    local result = copy(existing)
    result.active_titlebar_bg = palettes[s.palette].colors[1]
    result.inactive_titlebar_bg = '#101018'
    return result
  end

  local function apply(window, s)
    local override = copy(window:get_config_overrides())
    override.background = layers(s)
    override.text_background_opacity = s.mode == 'dream' and 0.96 or 1.0
    override.window_frame = frame(override.window_frame, s)
    window:set_config_overrides(override)
    s.initialized = true
  end

  -- Only focus fades and short pulses use Lua timers. APNG playback is native.
  local schedule
  schedule = function(window, s)
    if s.scheduled or s.mode ~= 'dream' then return end
    s.scheduled = true
    local generation = s.generation
    local id = window:window_id()
    wezterm.time.call_after(0.05, function()
      local current = (wezterm.GLOBAL.dreamstrata_window_effects or {})[tostring(id)]
      if generation ~= s.generation or not current or current.generation ~= generation then return end
      s.scheduled = false
      local ok = pcall(function()
        local now = clock()
        local dt = math.min(0.20, math.max(0.001, now - s.last))
        s.last = now
        s.focus = s.focus + (s.target - s.focus) * (1 - math.exp(-dt * 9))
        s.pulse = s.pulse * math.exp(-dt * 7)
        local moving = math.abs(s.focus - s.target) > 0.004 or s.pulse > 0.004
        if not moving then s.focus = s.target; s.pulse = 0 end
        apply(window, s)
        if moving then schedule(window, s) end
      end)
      if not ok then states[id] = nil end
    end)
  end

  local function pulse(window)
    local s = state(window)
    if s.mode ~= 'dream' then return end
    s.pulse = math.min(1, s.pulse + 0.75)
    s.last = clock()
    apply(window, s)
    schedule(window, s)
  end

  local function set_mode(window, mode)
    local s = state(window)
    s.generation = s.generation + 1
    s.scheduled = false
    s.mode = mode
    s.pulse = 0
    s.last = clock()
    s.target = window:is_focused() and 1 or 0.25
    s.focus = s.target
    remember(window, s)
    apply(window, s)
    if mode == 'dream' then pulse(window) end
  end

  local function set_palette(window, palette)
    local s = state(window)
    s.palette = palette
    remember(window, s)
    apply(window, s)
    pulse(window)
  end

  wezterm.on('update-status', function(window)
    local s = state(window)
    if not s.initialized then
      s.target = window:is_focused() and 1 or 0.25
      s.focus = s.target
      apply(window, s)
    end
  end)

  wezterm.on('window-focus-changed', function(window)
    local s = state(window)
    if s.mode ~= 'dream' then return end
    s.target = window:is_focused() and 1 or 0.25
    s.last = clock()
    if s.target == 1 then s.pulse = math.min(1, s.pulse + 0.3) end
    schedule(window, s)
  end)

  wezterm.on('bell', function(window) pulse(window) end)
  wezterm.on('dreamstrata-pulse', function(window) pulse(window) end)
  wezterm.on('dreamstrata-cycle-mode', function(window)
    local current = state(window).mode
    for index, mode in ipairs(modes) do
      if mode == current then set_mode(window, modes[index % #modes + 1]); break end
    end
  end)
  for _, mode in ipairs(modes) do
    local selected = mode
    wezterm.on('dreamstrata-mode-' .. selected, function(window) set_mode(window, selected) end)
  end
  for palette, _ in pairs(palettes) do
    local selected = palette
    wezterm.on('dreamstrata-palette-' .. selected, function(window) set_palette(window, selected) end)
  end

  wezterm.on('dreamstrata-effects-menu', function(window, pane)
    local s = state(window)
    local choices = {}
    for _, mode in ipairs(modes) do
      choices[#choices + 1] = { id = 'mode:' .. mode,
        label = (s.mode == mode and '● ' or '  ') .. names[mode] }
    end
    for _, palette in ipairs({ 'indigo', 'moss', 'ember' }) do
      choices[#choices + 1] = { id = 'palette:' .. palette,
        label = (s.palette == palette and '● ' or '  ') .. palettes[palette].label }
    end
    choices[#choices + 1] = { id = 'pulse', label = '泛起微光 / Soft pulse' }
    choices[#choices + 1] = { id = 'fullscreen', label = '全屏／窗口 / Fullscreen' }
    window:perform_action(wezterm.action.InputSelector {
      title = '梦层 · 本窗口效果 / Window effects',
      choices = choices,
      action = wezterm.action_callback(function(win, _, id)
        if not id then return end
        if id:sub(1, 5) == 'mode:' then set_mode(win, id:sub(6))
        elseif id:sub(1, 8) == 'palette:' then set_palette(win, id:sub(9))
        elseif id == 'pulse' then pulse(win)
        elseif id == 'fullscreen' then win:toggle_fullscreen() end
      end),
    }, pane)
  end)

  wezterm.on('augment-command-palette', function()
    return { { brief = '梦层：窗口效果 / Window effects',
      action = wezterm.action.EmitEvent 'dreamstrata-effects-menu' } }
  end)

  local initial = { mode = 'dream', palette = 'indigo', focus = 1, pulse = 0 }
  config.background = layers(initial)
  config.text_background_opacity = 0.96
  config.window_frame = frame(config.window_frame, initial)
  config.window_padding = { left = 6, right = 6, top = 12, bottom = 8 }
  config.animation_fps = 12
  config.status_update_interval = 1000
  local keys = config.keys or {}
  keys[#keys + 1] = { key = 'M', mods = 'CTRL|SHIFT', action = wezterm.action.EmitEvent 'dreamstrata-cycle-mode' }
  keys[#keys + 1] = { key = 'Space', mods = 'CTRL|SHIFT', action = wezterm.action.EmitEvent 'dreamstrata-effects-menu' }
  config.keys = keys
  local mouse = config.mouse_bindings or {}
  mouse[#mouse + 1] = { event = { Down = { streak = 1, button = 'Right' } },
    mods = 'CTRL|SHIFT', action = wezterm.action.EmitEvent 'dreamstrata-effects-menu' }
  -- In an application that grabs the mouse, WezTerm strips SHIFT before matching.
  mouse[#mouse + 1] = { event = { Down = { streak = 1, button = 'Right' } },
    mods = 'CTRL', mouse_reporting = false, alt_screen = true,
    action = wezterm.action.EmitEvent 'dreamstrata-effects-menu' }
  config.mouse_bindings = mouse
end
