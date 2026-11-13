extends Node3D

const PLAYER_SCRIPT = preload("res://demo/player.gd")
const PIE_SCRIPT = preload("res://demo/projectile.gd")

enum Phase { MENU, PLAYING, ROUND_RESULT, MATCH_RESULT }

const ARENA_BOUNDS := Vector2(7.7, 5.0)
const ROUND_LENGTH := 42.0
const ROUND_RESULT_LENGTH := 2.7
const MATCH_ROUNDS := 3
const CHARACTER_MODELS := [
	"res://models/glb/01_giraffe.glb",
	"res://models/glb/02_rabbit.glb",
	"res://models/glb/03_dragon.glb",
	"res://models/glb/04_lion.glb",
	"res://models/glb/05_snake.glb",
	"res://models/glb/06_panda.glb",
	"res://models/glb/07_shark.glb"
]
const CHARACTER_NAMES := ["GIRAFFE", "BUNNY", "DRAGON", "LION", "SNAKE", "PANDA", "SHARK"]
const PLAYER_COLORS := [Color("#ffbf44"), Color("#f78ea4"), Color("#f04b3e"), Color("#9a6b50")]
const SPAWNS := [Vector3(-5.4, 0, -3.1), Vector3(5.4, 0, 3.1), Vector3(-5.4, 0, 3.1), Vector3(5.4, 0, -3.1)]

var phase := Phase.MENU
var players: Array[ArenaPlayer] = []
var projectiles: Array[ArenaPie] = []
var scores := [0, 0, 0, 0]
var eliminations := [0, 0, 0, 0]
var round_index := 1
var round_time := ROUND_LENGTH
var phase_time := 0.0
var human_count := 1
var round_winner_ids: Array[int] = []
var rng := RandomNumberGenerator.new()
var arena_root: Node3D
var hud: CanvasLayer
var title_label: Label
var status_label: Label
var instruction_label: Label
var result_panel: ColorRect
var result_label: Label
var world_environment: WorldEnvironment
var throw_count := 0
var round_count := 0

func _ready() -> void:
	rng.seed = 20261113
	_setup_input()
	_build_arena()
	_build_hud()
	_update_menu()
	if OS.get_cmdline_user_args().has("--autostart"):
		start_match()
	if OS.get_cmdline_user_args().has("--headless_test"):
		var test_seconds := 5.0
		for arg in OS.get_cmdline_user_args():
			if arg.begins_with("--test_seconds="):
				test_seconds = maxf(1.0, float(arg.get_slice("=", 1)))
		get_tree().create_timer(test_seconds).timeout.connect(_finish_headless_test)
	if OS.get_cmdline_user_args().has("--capture_demo"):
		get_tree().create_timer(1.15).timeout.connect(_capture_frame)

func _finish_headless_test() -> void:
	print("HEADLESS_DEMO_TEST throws=%d rounds=%d alive=%d" % [throw_count, round_count, _alive_count()])
	get_tree().quit()

func _capture_frame() -> void:
	if DisplayServer.get_name() == "headless":
		return
	var viewport_texture := get_viewport().get_texture()
	if viewport_texture != null:
		viewport_texture.get_image().save_png("res://demo_capture.png")

func _setup_input() -> void:
	var bindings := {
		"p1_up": [KEY_W], "p1_down": [KEY_S], "p1_left": [KEY_A], "p1_right": [KEY_D], "p1_throw": [KEY_F], "p1_block": [KEY_SPACE],
		"p2_up": [KEY_UP], "p2_down": [KEY_DOWN], "p2_left": [KEY_LEFT], "p2_right": [KEY_RIGHT], "p2_throw": [KEY_ENTER], "p2_block": [KEY_SHIFT],
		"p3_up": [KEY_I], "p3_down": [KEY_K], "p3_left": [KEY_J], "p3_right": [KEY_L], "p3_throw": [KEY_O], "p3_block": [KEY_P],
		"p4_up": [KEY_Z], "p4_down": [KEY_X], "p4_left": [KEY_C], "p4_right": [KEY_V], "p4_throw": [KEY_B], "p4_block": [KEY_N]
	}
	for action in bindings:
		if not InputMap.has_action(action):
			InputMap.add_action(action)
		for key in bindings[action]:
			var event := InputEventKey.new()
			event.physical_keycode = key
			InputMap.action_add_event(action, event)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if phase == Phase.MENU:
			if event.keycode in [KEY_1, KEY_2, KEY_3, KEY_4]:
				human_count = clampi(event.keycode - KEY_0, 1, 4)
				_update_menu()
			elif event.keycode in [KEY_ENTER, KEY_SPACE]:
				start_match()
		elif phase == Phase.MATCH_RESULT and event.keycode in [KEY_ENTER, KEY_SPACE, KEY_R]:
			start_match()
		elif phase == Phase.ROUND_RESULT and event.keycode == KEY_ESCAPE:
			start_match()

func _build_arena() -> void:
	arena_root = Node3D.new()
	arena_root.name = "Arena"
	add_child(arena_root)
	world_environment = WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("#170f36")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color("#b6a7e8")
	env.ambient_light_energy = 0.55
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world_environment.environment = env
	add_child(world_environment)
	var floor := MeshInstance3D.new()
	var floor_mesh := PlaneMesh.new()
	floor_mesh.size = Vector2(17.2, 11.8)
	var floor_mat := StandardMaterial3D.new()
	floor_mat.albedo_color = Color("#332762")
	floor_mat.roughness = 0.78
	floor_mat.metallic = 0.04
	floor_mesh.material = floor_mat
	floor.mesh = floor_mesh
	floor.rotation.x = -PI / 2.0
	arena_root.add_child(floor)
	for x in [-8.25, 8.25]:
		_add_box(Vector3(x, 0.75, 0), Vector3(0.35, 1.5, 11.5), Color("#5c42a2"), "Wall")
	for z in [-5.65, 5.65]:
		_add_box(Vector3(0, 0.75, z), Vector3(16.8, 1.5, 0.35), Color("#5c42a2"), "Wall")
	# Center dais and corner pads make the space readable from the high camera.
	_add_cylinder(Vector3(0, 0.03, 0), Vector2(2.05, 2.05), 0.11, Color("#49388a"), "CenterDais")
	for pos in [Vector3(-6.5, 0.04, 0), Vector3(6.5, 0.04, 0), Vector3(0, 0.04, -4.1), Vector3(0, 0.04, 4.1)]:
		_add_cylinder(pos, Vector2(0.95, 0.95), 0.055, Color("#7a54b9"), "Pad")
	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52, -24, 0)
	sun.light_energy = 1.25
	sun.light_color = Color("#fff1e2")
	arena_root.add_child(sun)
	var fill := OmniLight3D.new()
	fill.position = Vector3(0, 5.4, 0)
	fill.light_energy = 8.0
	fill.omni_range = 16.0
	fill.light_color = Color("#9a82ff")
	arena_root.add_child(fill)
	var camera := Camera3D.new()
	camera.name = "ArenaCamera"
	camera.position = Vector3(0, 13.8, 8.8)
	camera.rotation = (Vector3(0, 0, 0) - camera.position).normalized().slerp(Vector3.DOWN, 0.12).cross(Vector3.RIGHT).normalized() # overwritten below
	camera.look_at_from_position(camera.position, Vector3(0, 0, 0), Vector3.UP)
	camera.fov = 46.0
	arena_root.add_child(camera)
	camera.current = true

func _add_box(pos: Vector3, size: Vector3, color: Color, title: String) -> void:
	var node := MeshInstance3D.new()
	node.name = title
	var mesh := BoxMesh.new()
	mesh.size = size
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.65
	mesh.material = mat
	node.mesh = mesh
	node.position = pos
	arena_root.add_child(node)

func _add_cylinder(pos: Vector3, size: Vector2, height: float, color: Color, title: String) -> void:
	var node := MeshInstance3D.new()
	node.name = title
	var mesh := CylinderMesh.new()
	mesh.top_radius = size.x * 0.5
	mesh.bottom_radius = size.y * 0.5
	mesh.height = height
	var mat := StandardMaterial3D.new()
	mat.albedo_color = color
	mat.roughness = 0.72
	mesh.material = mat
	node.mesh = mesh
	node.position = pos
	arena_root.add_child(node)

func _build_hud() -> void:
	hud = CanvasLayer.new()
	hud.name = "HUD"
	add_child(hud)
	var top_bar := ColorRect.new()
	top_bar.color = Color(0.03, 0.02, 0.08, 0.82)
	top_bar.position = Vector2(0, 0)
	top_bar.size = Vector2(1280, 76)
	hud.add_child(top_bar)
	title_label = _make_label("ANIMAL ARENA", Vector2(30, 15), 30, Color("#ffe7b1"))
	hud.add_child(title_label)
	status_label = _make_label("", Vector2(420, 19), 22, Color("#ffffff"))
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.size.x = 500
	hud.add_child(status_label)
	instruction_label = _make_label("", Vector2(28, 662), 18, Color("#d8c9ff"))
	instruction_label.size.x = 1220
	hud.add_child(instruction_label)
	result_panel = ColorRect.new()
	result_panel.color = Color(0.035, 0.02, 0.10, 0.90)
	result_panel.position = Vector2(250, 190)
	result_panel.size = Vector2(780, 330)
	result_panel.visible = false
	hud.add_child(result_panel)
	result_label = _make_label("", Vector2(275, 220), 28, Color("#ffffff"))
	result_label.size = Vector2(730, 270)
	result_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	result_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	result_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	result_label.visible = false
	hud.add_child(result_label)

func _make_label(text_value: String, pos: Vector2, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text_value
	label.position = pos
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	return label

func _update_menu() -> void:
	phase = Phase.MENU
	result_panel.visible = true
	result_label.visible = true
	result_label.text = "ANIMAL ARENA\n\n1–4 选择本地玩家数量（当前 %d 人）\nENTER / SPACE 开始\n\nP1  WASD + F 投掷 + SPACE 格挡\nP2  方向键 + ENTER 投掷 + SHIFT 格挡\nP3  IJKL + O 投掷 + P 格挡\nP4  ZXCV + B 投掷 + N 格挡\n\n最后存活者赢得本回合，三回合后结算" % human_count
	instruction_label.text = "参考玩法：Pie Noon 的投掷淘汰 + Starship Olympics 的本地多人 / AI 对手结构"
	status_label.text = "LOCAL PARTY DEMO"

func start_match() -> void:
	for player in players:
		if is_instance_valid(player):
			player.queue_free()
	players.clear()
	for pie in projectiles:
		if is_instance_valid(pie):
			pie.queue_free()
	projectiles.clear()
	scores = [0, 0, 0, 0]
	eliminations = [0, 0, 0, 0]
	round_index = 1
	_create_players()
	result_panel.visible = false
	result_label.visible = false
	phase = Phase.PLAYING
	_start_round()

func _create_players() -> void:
	for i in range(4):
		var player := PLAYER_SCRIPT.new() as ArenaPlayer
		player.name = "Player%d" % (i + 1)
		var prefix := "p%d" % (i + 1)
		player.setup(i, "P%d %s" % [i + 1, CHARACTER_NAMES[i]], CHARACTER_MODELS[i], PLAYER_COLORS[i], i < human_count, prefix, SPAWNS[i])
		player.throw_requested.connect(_on_throw_requested)
		player.eliminated.connect(_on_player_eliminated)
		add_child(player)
		players.append(player)

func _start_round() -> void:
	phase = Phase.PLAYING
	round_time = ROUND_LENGTH
	phase_time = 0.0
	round_winner_ids.clear()
	for i in range(players.size()):
		players[i].reset_for_round(SPAWNS[i])
	for pie in projectiles:
		if is_instance_valid(pie):
			pie.queue_free()
	projectiles.clear()
	_update_hud()

func _physics_process(delta: float) -> void:
	match phase:
		Phase.PLAYING:
			_tick_playing(delta)
		Phase.ROUND_RESULT, Phase.MATCH_RESULT:
			phase_time -= delta
			if phase == Phase.ROUND_RESULT and phase_time <= 0.0:
				if round_index < MATCH_ROUNDS:
					round_index += 1
					_start_round()
			if phase == Phase.MATCH_RESULT and phase_time <= 0.0:
				_update_menu()

func _tick_playing(delta: float) -> void:
	round_time = maxf(0.0, round_time - delta)
	for player in players:
		if not player.alive:
			continue
		if not player.is_human:
			_ai_think(player, delta)
		player.tick(delta, ARENA_BOUNDS)
	for pie in projectiles.duplicate():
		if not is_instance_valid(pie):
			projectiles.erase(pie)
			continue
		pie.tick(delta, ARENA_BOUNDS)
		if not pie.active:
			projectiles.erase(pie)
			pie.queue_free()
			continue
		_check_pie_hits(pie)
	if _should_end_round():
		_end_round()
	_update_hud()

func _ai_think(player: ArenaPlayer, delta: float) -> void:
	var target: ArenaPlayer = _nearest_target(player)
	if target == null:
		player.set_ai_intent(Vector2.ZERO, Vector3.FORWARD, false, false)
		return
	var to_target := target.global_position - player.global_position
	to_target.y = 0.0
	var direction := to_target.normalized()
	var move := Vector2(direction.x, direction.z)
	# Threat avoidance mirrors Pie Noon’s danger-first AI priority.
	var threat := _incoming_threat(player)
	var wants_block := threat != null and player.block_cooldown <= 0.0 and rng.randf() < 0.12
	if threat != null and not wants_block:
		var away := (player.global_position - threat.global_position).normalized()
		move = Vector2(away.x, away.z) + Vector2(-away.z, away.x) * 0.42
	var wants_throw := player.throw_cooldown <= 0.0 and to_target.length() < 8.8 and rng.randf() < delta * 0.65
	player.set_ai_intent(move, direction, wants_throw, wants_block)

func _nearest_target(player: ArenaPlayer) -> ArenaPlayer:
	var best: ArenaPlayer
	var best_distance := INF
	for other in players:
		if other == player or not other.alive:
			continue
		var d := player.global_position.distance_squared_to(other.global_position)
		if d < best_distance:
			best_distance = d
			best = other
	return best

func _incoming_threat(player: ArenaPlayer) -> ArenaPie:
	var best: ArenaPie
	var best_distance := 3.5
	for pie in projectiles:
		if not is_instance_valid(pie) or pie.owner_id == player.player_id or pie.age < 0.18:
			continue
		var distance := pie.global_position.distance_to(player.global_position)
		if distance < best_distance and pie.velocity.dot(player.global_position - pie.global_position) > 0.0:
			best = pie
			best_distance = distance
	return best

func _on_throw_requested(player: ArenaPlayer, origin: Vector3, direction: Vector3) -> void:
	if phase != Phase.PLAYING:
		return
	var pie := PIE_SCRIPT.new() as ArenaPie
	pie.name = "Pie_%d_%d" % [player.player_id, Time.get_ticks_msec()]
	pie.setup(player.player_id, origin, direction, player.player_color)
	add_child(pie)
	projectiles.append(pie)
	throw_count += 1

func _check_pie_hits(pie: ArenaPie) -> void:
	for player in players:
		if not player.alive or player.player_id == pie.owner_id or pie.age < 0.18:
			continue
		if pie.global_position.distance_to(player.global_position + Vector3.UP * 0.72) < 0.62:
			if player.blocking:
				var reflected := (pie.global_position - player.global_position).normalized()
				reflected.y = 0.0
				pie.velocity = reflected.normalized() * ArenaPie.SPEED * 1.12
				pie.owner_id = player.player_id
				pie.age = 0.0
				player.consume_block()
				return
			player.eliminate()
			eliminations[pie.owner_id] += 1
			pie.active = false
			return

func _on_player_eliminated(player: ArenaPlayer) -> void:
	player.hit_flash = 0.8

func _should_end_round() -> bool:
	var alive_count := 0
	for player in players:
		if player.alive:
			alive_count += 1
	return alive_count <= 1 or round_time <= 0.0

func _end_round() -> void:
	if phase != Phase.PLAYING:
		return
	phase = Phase.ROUND_RESULT
	round_count += 1
	phase_time = ROUND_RESULT_LENGTH
	for player in players:
		if player.alive:
			round_winner_ids.append(player.player_id)
	if round_winner_ids.is_empty():
		# Time-out tie breaker: highest elimination count, then nearest to center.
		var best_score := -1
		for player in players:
			if eliminations[player.player_id] > best_score:
				best_score = eliminations[player.player_id]
				round_winner_ids = [player.player_id]
	for winner_id in round_winner_ids:
		scores[winner_id] += 1
	var names: Array[String] = []
	for winner_id in round_winner_ids:
		names.append(players[winner_id].player_name)
	if round_index >= MATCH_ROUNDS:
		_end_match(names)
	else:
		result_panel.visible = true
		result_label.visible = true
		result_label.text = "ROUND %d COMPLETE\n\n%s\n\nNext round in %.1f" % [round_index, " + ".join(names) if not names.is_empty() else "DRAW", phase_time]

func _end_match(last_round_names: Array[String]) -> void:
	phase = Phase.MATCH_RESULT
	phase_time = 7.0
	var best: int = int(scores.max())
	var winners: Array[String] = []
	for i in range(scores.size()):
		if scores[i] == best:
			winners.append(players[i].player_name)
	var lines: Array[String] = []
	for i in range(players.size()):
		lines.append("%s    %d rounds    %d hits" % [players[i].player_name, scores[i], eliminations[i]])
	result_panel.visible = true
	result_label.visible = true
	result_label.text = "MATCH COMPLETE\n\nWINNER\n%s\n\n%s\n\nPress ENTER to play again" % [" + ".join(winners), "\n".join(lines)]

func _update_hud() -> void:
	if phase == Phase.PLAYING:
		var alive_names: Array[String] = []
		for player in players:
			if player.alive:
				alive_names.append(player.player_name)
		status_label.text = "ROUND %d / %d     %02d s     ALIVE %d     %s" % [round_index, MATCH_ROUNDS, ceili(round_time), alive_names.size(), "  ".join(alive_names)]
		instruction_label.text = "P1 WASD/F/SPACE     P2 ARROWS/ENTER/SHIFT     P3 IJKL/O/P     P4 ZXCV/B/N     Throw pies, block, survive"
		result_panel.visible = false
		result_label.visible = false

func _alive_count() -> int:
	var count := 0
	for player in players:
		if player.alive:
			count += 1
	return count

