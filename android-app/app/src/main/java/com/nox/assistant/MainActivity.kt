package com.nox.assistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNeededPermissions()
        NoxTts.init(applicationContext)

        if (!Prefs.wasGreetedThisSession(applicationContext)) {
            NoxTts.speak("Good morning. NOX is here. How can I help you?")
            Prefs.setGreetedThisSession(applicationContext, true)
        }

        setContent {
            NoxTheme { NoxApp() }
        }
    }

    private fun requestNeededPermissions() {
        val perms = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            perms.add(Manifest.permission.POST_NOTIFICATIONS)
        }
        val needed = perms.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (needed.isNotEmpty()) permissionLauncher.launch(needed.toTypedArray())
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NoxApp() {
    var tab by remember { mutableStateOf(0) }
    val tabs = listOf("Chat", "Training", "Memory", "Settings")

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("NOX", color = NoxAccent) },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = NoxSurface)
            )
        },
        bottomBar = {
            NavigationBar(containerColor = NoxSurface) {
                tabs.forEachIndexed { i, label ->
                    NavigationBarItem(
                        selected = tab == i,
                        onClick = { tab = i },
                        icon = {},
                        label = { Text(label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = NoxAccent,
                            selectedTextColor = NoxAccent,
                            indicatorColor = NoxSurfaceVariant
                        )
                    )
                }
            }
        },
        containerColor = NoxBackground
    ) { padding ->
        Box(Modifier.padding(padding)) {
            when (tab) {
                0 -> ChatScreen()
                1 -> TrainingScreen()
                2 -> MemoryScreen()
                3 -> SettingsScreen()
            }
        }
    }
}

sealed class ChatItem
data class UserMessage(val text: String) : ChatItem()
data class AssistantMessage(val text: String) : ChatItem()
data class StatusLine(val text: String) : ChatItem()

@Composable
fun ChatBubble(text: String, isUser: Boolean) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start) {
        Box(
            Modifier
                .padding(vertical = 4.dp)
                .clip(RoundedCornerShape(14.dp))
                .background(if (isUser) NoxAccent else NoxSurface)
                .padding(horizontal = 14.dp, vertical = 10.dp)
                .widthIn(max = 280.dp)
        ) {
            Text(text, color = if (isUser) NoxBackground else NoxTextPrimary)
        }
    }
}

@Composable
fun StatusRow(text: String) {
    Text(
        "· $text",
        color = NoxTextSecondary,
        fontStyle = FontStyle.Italic,
        modifier = Modifier.padding(vertical = 2.dp)
    )
}

@Composable
fun ChatScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val scope = rememberCoroutineScope()
    var input by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var sending by remember { mutableStateOf(false) }
    val items = remember { mutableStateListOf<ChatItem>() }
    var streamingText by remember { mutableStateOf("") }
    var isStreaming by remember { mutableStateOf(false) }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        if (error != null) {
            Text("Connection error: $error", color = androidx.compose.ui.graphics.Color(0xFFE07A5F))
        }
        LazyColumn(Modifier.weight(1f)) {
            items(items) { item ->
                when (item) {
                    is UserMessage -> ChatBubble(item.text, isUser = true)
                    is AssistantMessage -> ChatBubble(item.text, isUser = false)
                    is StatusLine -> StatusRow(item.text)
                }
            }
            if (isStreaming) {
                item { ChatBubble(streamingText.ifEmpty { "..." }, isUser = false) }
            }
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                value = input, onValueChange = { input = it },
                modifier = Modifier.weight(1f), placeholder = { Text("Message NOX...") },
                enabled = !sending
            )
            Spacer(Modifier.width(8.dp))
            Button(
                onClick = {
                    val text = input.trim()
                    if (text.isEmpty() || sending) return@Button
                    items.add(UserMessage(text))
                    input = ""
                    error = null
                    sending = true
                    isStreaming = true
                    streamingText = ""
                    scope.launch {
                        try {
                            StreamClient.chatStream(context, text) { event ->
                                when (event.type) {
                                    "status" -> {
                                        items.add(StatusLine(event.text ?: ""))
                                    }
                                    "token" -> {
                                        streamingText += event.text ?: ""
                                    }
                                    "done" -> {
                                        items.add(AssistantMessage(event.reply ?: streamingText))
                                        isStreaming = false
                                        streamingText = ""
                                    }
                                }
                            }
                        } catch (e: Exception) {
                            error = e.message ?: "could not reach the brain server"
                            isStreaming = false
                        }
                        sending = false
                    }
                },
                colors = ButtonDefaults.buttonColors(containerColor = NoxAccent)
            ) { Text("Send", color = NoxBackground) }
        }
    }
}

@Composable
fun TrainingScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val scope = rememberCoroutineScope()
    var textInput by remember { mutableStateOf("") }
    var urlInput by remember { mutableStateOf("") }
    var items by remember { mutableStateOf(listOf<KnowledgeItem>()) }
    var error by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        scope.launch {
            try {
                items = ApiClient.get(context).listKnowledge()
                error = null
            } catch (e: Exception) {
                error = e.message ?: "could not reach the brain server"
            }
        }
    }
    LaunchedEffect(Unit) { refresh() }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        if (error != null) Text("Connection error: $error", color = androidx.compose.ui.graphics.Color(0xFFE07A5F))
        OutlinedTextField(value = textInput, onValueChange = { textInput = it }, label = { Text("Text to teach NOX") }, modifier = Modifier.fillMaxWidth())
        Button(onClick = {
            scope.launch {
                try {
                    ApiClient.get(context).addTextKnowledge(TextKnowledgeRequest(textInput))
                    textInput = ""
                } catch (e: Exception) {
                    error = e.message ?: "could not reach the brain server"
                }
                refresh()
            }
        }, colors = ButtonDefaults.buttonColors(containerColor = NoxAccent)) { Text("Add Text", color = NoxBackground) }

        Spacer(Modifier.height(8.dp))
        OutlinedTextField(value = urlInput, onValueChange = { urlInput = it }, label = { Text("URL") }, modifier = Modifier.fillMaxWidth())
        Button(onClick = {
            scope.launch {
                try {
                    ApiClient.get(context).addUrlKnowledge(UrlKnowledgeRequest(urlInput))
                    urlInput = ""
                } catch (e: Exception) {
                    error = e.message ?: "could not reach the brain server"
                }
                refresh()
            }
        }, colors = ButtonDefaults.buttonColors(containerColor = NoxAccent)) { Text("Add URL", color = NoxBackground) }

        Spacer(Modifier.height(12.dp))
        Text("Trained knowledge:", color = NoxTextSecondary)
        LazyColumn(Modifier.weight(1f)) {
            items(items) { item ->
                Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("[${item.source_type}] ${item.source_name}", color = NoxTextPrimary)
                    TextButton(onClick = {
                        scope.launch {
                            try {
                                ApiClient.get(context).deleteKnowledge(item.id)
                            } catch (e: Exception) {
                                error = e.message ?: "could not reach the brain server"
                            }
                            refresh()
                        }
                    }) { Text("Delete", color = NoxAccent) }
                }
            }
        }
    }
}

@Composable
fun MemoryScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val scope = rememberCoroutineScope()
    var input by remember { mutableStateOf("") }
    var items by remember { mutableStateOf(listOf<MemoryItem>()) }
    var error by remember { mutableStateOf<String?>(null) }

    fun refresh() {
        scope.launch {
            try {
                items = ApiClient.get(context).listMemory()
                error = null
            } catch (e: Exception) {
                error = e.message ?: "could not reach the brain server"
            }
        }
    }
    LaunchedEffect(Unit) { refresh() }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        if (error != null) Text("Connection error: $error", color = androidx.compose.ui.graphics.Color(0xFFE07A5F))
        OutlinedTextField(value = input, onValueChange = { input = it }, label = { Text("Fact to remember") }, modifier = Modifier.fillMaxWidth())
        Button(onClick = {
            scope.launch {
                try {
                    ApiClient.get(context).addMemory(MemoryRequest(input))
                    input = ""
                } catch (e: Exception) {
                    error = e.message ?: "could not reach the brain server"
                }
                refresh()
            }
        }, colors = ButtonDefaults.buttonColors(containerColor = NoxAccent)) { Text("Remember", color = NoxBackground) }

        Spacer(Modifier.height(12.dp))
        LazyColumn(Modifier.weight(1f)) {
            items(items) { item ->
                Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(item.fact, color = NoxTextPrimary)
                    TextButton(onClick = {
                        scope.launch {
                            try {
                                ApiClient.get(context).deleteMemory(item.id)
                            } catch (e: Exception) {
                                error = e.message ?: "could not reach the brain server"
                            }
                            refresh()
                        }
                    }) { Text("Forget", color = NoxAccent) }
                }
            }
        }
    }
}

@Composable
fun SettingsScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val scope = rememberCoroutineScope()
    var serverUrl by remember { mutableStateOf(Prefs.getServerUrl(context)) }
    var voiceEnabled by remember { mutableStateOf(Prefs.isVoiceEnabled(context)) }
    var personality by remember { mutableStateOf("") }
    var savedMsg by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        try {
            personality = ApiClient.get(context).getPersonality().text
        } catch (_: Exception) {}
    }

    Column(Modifier.fillMaxSize().padding(12.dp).verticalScroll(rememberScrollState())) {
        Text("Brain server address (your laptop's local IP):", color = NoxTextSecondary)
        OutlinedTextField(
            value = serverUrl, onValueChange = { serverUrl = it },
            modifier = Modifier.fillMaxWidth()
        )
        Button(onClick = {
            Prefs.setServerUrl(context, serverUrl)
            savedMsg = "Address saved."
        }, colors = ButtonDefaults.buttonColors(containerColor = NoxAccent)) { Text("Save Address", color = NoxBackground) }

        Spacer(Modifier.height(16.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Switch(
                checked = voiceEnabled,
                onCheckedChange = {
                    voiceEnabled = it
                    Prefs.setVoiceEnabled(context, it)
                    try {
                        val intent = Intent(context, NoxWakeService::class.java)
                        if (it) context.startForegroundService(intent) else context.stopService(intent)
                    } catch (e: Exception) {
                        savedMsg = "Voice service error: ${e.message}"
                    }
                },
                colors = SwitchDefaults.colors(checkedThumbColor = NoxAccent)
            )
            Spacer(Modifier.width(8.dp))
            Text("Enable voice control (\"hey nox\" / \"nox sleep\")", color = NoxTextPrimary)
        }

        Spacer(Modifier.height(24.dp))
        Text("Custom personality / instructions for NOX:", color = NoxTextSecondary)
        OutlinedTextField(
            value = personality, onValueChange = { personality = it },
            modifier = Modifier.fillMaxWidth().height(160.dp)
        )
        Button(onClick = {
            scope.launch {
                try {
                    ApiClient.get(context).setPersonality(PersonalityText(personality))
                    savedMsg = "Personality saved."
                } catch (e: Exception) {
                    savedMsg = "Could not save: ${e.message}"
                }
            }
        }, colors = ButtonDefaults.buttonColors(containerColor = NoxAccent)) { Text("Save Personality", color = NoxBackground) }

        if (savedMsg != null) {
            Spacer(Modifier.height(8.dp))
            Text(savedMsg!!, color = NoxTextSecondary)
        }
    }
}
