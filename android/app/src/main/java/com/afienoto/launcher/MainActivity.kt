package com.afienoto.launcher

import android.content.ActivityNotFoundException
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.afienoto.launcher.databinding.ActivityMainBinding

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.openBotButton.setOnClickListener { openBot() }
    }

    private fun openBot() {
        val deepLink = Intent(Intent.ACTION_VIEW, Uri.parse("tg://resolve?domain=${BuildConfig.BOT_USERNAME}"))
        try {
            startActivity(deepLink)
        } catch (e: ActivityNotFoundException) {
            val webLink = Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me/${BuildConfig.BOT_USERNAME}"))
            startActivity(webLink)
        }
    }
}
