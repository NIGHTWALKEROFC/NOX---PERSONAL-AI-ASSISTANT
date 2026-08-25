package com.nox.assistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
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

        setContent { NoxApp() }
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
        topBar = { TopAppBar(title = { Text("NOX") }) },
        bottomBar = {
            NavigationBar {
                tabs.forEachIndexed { i, label ->
                    NavigationBarItem(
                        selected = tab == i,
                        onClick = { tab = i },
                        icon = {},
                        label = { Text(label) }
                    )
                }
            }
        }
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

@Composable
fun ErrorBanner(message: String?) {
    if (message != null) {
        Text(
            "Connection error: $message",
            color = Color.Red,
            modifier = Modifier.padding(8.dp)
        )
    }
}

@Composable
fun ChatScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current
    val scope = rememberCoroutineScope()
    var input by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    val messages = remember { mutableStateListOf<Pair<String, String>>() }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        ErrorBanner(error)
        LazyColumn(Modifier.weight(1f)) {
            items(messages) { (who, text) ->
                Text("$who: $text", modifier = Modifier.padding(vertical = 4.dp))
            }
        }
        Row {
            OutlinedTextField(
                value = input, onValueChange = { input = it },
                modifier = Modifier.weight(1f), placeholder = { Text("Message NOX...") }
            )
            Spacer(Modifier.width(8.dp))
            Button(onClick = {
                val text = input.trim()
                if (text.isEmpty()) return@Button
                messages.add("You" to text)
                input = ""
                error = null
                scope.launch {
                    try {
                        val api = ApiClient.get(context)
                        val sessionId = Prefs.getSessionId(context)
                        val result = api.chat(ChatRequest(sessionId, text, speak = false))
                        messages.add("NOX" to result.reply)
                    } catch (e: Exception) {
                        error = e.message ?: "could not reach the brain server"
                    }
                }
            }) { Text("Send") }
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
        ErrorBanner(error)
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
        }) { Text("Add Text") }

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
        }) { Text("Add URL") }

        Spacer(Modifier.height(12.dp))
        Text("Trained knowledge:")
        LazyColumn(Modifier.weight(1f)) {
            items(items) { item ->
                Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("[${item.source_type}] ${item.source_name}")
                    TextButton(onClick = {
                        scope.launch {
                            try {
                                ApiClient.get(context).deleteKnowledge(item.id)
                            } catch (e: Exception) {
                                error = e.message ?: "could not reach the brain server"
                            }
                            refresh()
                        }
                    }) { Text("Delete") }
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
        ErrorBanner(error)
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
        }) { Text("Remember") }

        Spacer(Modifier.height(12.dp))
        LazyColumn(Modifier.weight(1f)) {
            items(items) { item ->
                Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(item.fact)
                    TextButton(onClick = {
                        scope.launch {
                            try {
                                ApiClient.get(context).deleteMemory(item.id)
                            } catch (e: Exception) {
                                error = e.message ?: "could not reach the brain server"
                            }
                            refresh()
                        }
                    }) { Text("Forget") }
                }
            }
        }
    }
}

@Composable
fun SettingsScreen() {
    val context = androidx.compose.ui.platform.LocalContext.current
    var serverUrl by remember { mutableStateOf(Prefs.getServerUrl(context)) }
    var voiceEnabled by remember { mutableStateOf(Prefs.isVoiceEnabled(context)) }
    var savedMsg by remember { mutableStateOf<String?>(null) }

    Column(Modifier.fillMaxSize().padding(12.dp)) {
        Text("Brain server address (your laptop's local IP):")
        OutlinedTextField(
            value = serverUrl, onValueChange = { serverUrl = it },
            modifier = Modifier.fillMaxWidth()
        )
        Button(onClick = {
            Prefs.setServerUrl(context, serverUrl)
            savedMsg = "Saved."
        }) { Text("Save Address") }
        if (savedMsg != null) Text(savedMsg!!, color = Color.Gray)

        Spacer(Modifier.height(16.dp))
        Row(verticalAlignment = androidx.compose.ui.Alignment.CenterVertically) {
            Switch(checked = voiceEnabled, onCheckedChange = {
                voiceEnabled = it
                Prefs.setVoiceEnabled(context, it)
                try {
                    val intent = Intent(context, NoxWakeService::class.java)
                    if (it) context.startForegroundService(intent) else context.stopService(intent)
                } catch (e: Exception) {
                    savedMsg = "Voice service error: ${e.message}"
                }
            })
            Spacer(Modifier.width(8.dp))
            Text("Enable voice control (\"hey nox\" / \"nox sleep\")")
        }
    }
}
